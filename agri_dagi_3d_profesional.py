import numpy as np
import rasterio
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import plotly.offline as pyo
from scipy.ndimage import gaussian_filter
from scipy.interpolate import griddata
from skimage import filters
import os

class AgriDagi3D:
    def __init__(self, dem_path, roughness_path=None):
        self.dem_path = dem_path
        self.roughness_path = roughness_path
        self.dem_data = None
        self.roughness_data = None
        self.slope_data = None
        self.aspect_data = None
        self.hillshade_data = None
        self.transform = None
        self.crs = None
        
        self._load_data()
        
    def _load_data(self):
        """Veri setlerini yükle ve ön işleme yap"""
        print("📊 Veri yükleniyor ve işleniyor...")
        
        # DEM verisi
        with rasterio.open(self.dem_path) as dataset:
            self.dem_data = dataset.read(1).astype(float)
            self.transform = dataset.transform
            self.crs = dataset.crs
            
            # NoData değerlerini interpolasyon ile doldur
            if dataset.nodata is not None:
                mask = self.dem_data == dataset.nodata
                self.dem_data[mask] = np.nan
                self._interpolate_missing_values()
        
        # Roughness verisi (varsa)
        if self.roughness_path and os.path.exists(self.roughness_path):
            with rasterio.open(self.roughness_path) as dataset:
                self.roughness_data = dataset.read(1).astype(float)
                if dataset.nodata is not None:
                    mask = self.roughness_data == dataset.nodata
                    self.roughness_data[mask] = np.nan
        
        # Türetilmiş haritaları hesapla
        self._calculate_derived_maps()
        
        print(f"✅ Veri yükleme tamamlandı: {self.dem_data.shape}")
        
    def _interpolate_missing_values(self):
        """Eksik değerleri interpolasyon ile doldur"""
        mask = ~np.isnan(self.dem_data)
        if np.sum(mask) < 0.5 * self.dem_data.size:
            return
            
        y, x = np.mgrid[0:self.dem_data.shape[0], 0:self.dem_data.shape[1]]
        valid_points = np.column_stack((y[mask], x[mask]))
        valid_values = self.dem_data[mask]
        
        missing_points = np.column_stack((y[~mask], x[~mask]))
        
        if len(missing_points) > 0:
            interpolated = griddata(valid_points, valid_values, missing_points, 
                                  method='cubic', fill_value=np.nanmean(valid_values))
            self.dem_data[~mask] = interpolated
    
    def _calculate_derived_maps(self):
        """Türetilmiş haritaları hesapla"""
        print("🗺️ Türetilmiş haritalar hesaplanıyor...")
        
        # Piksel boyutu (metre cinsinden)
        pixel_size = abs(self.transform[0])
        if self.crs and 'EPSG:4326' in self.crs.to_string():
            pixel_size *= 111000  # Derece -> metre (yaklaşık)
        
        # Eğim hesaplama (gelişmiş algoritma)
        self.slope_data = self._calculate_slope_advanced(pixel_size)
        
        # Aspect (bakı) hesaplama
        self.aspect_data = self._calculate_aspect(pixel_size)
        
        # Hillshade (gölgeleme) hesaplama
        self.hillshade_data = self._calculate_hillshade()
        
    def _calculate_slope_advanced(self, pixel_size):
        """Gelişmiş eğim hesaplama algoritması"""
        smoothed_dem = gaussian_filter(self.dem_data, sigma=1.0)
        grad_x = filters.sobel_h(smoothed_dem) / (8 * pixel_size)
        grad_y = filters.sobel_v(smoothed_dem) / (8 * pixel_size)
        slope_rad = np.arctan(np.sqrt(grad_x**2 + grad_y**2))
        slope_deg = np.degrees(slope_rad)
        return np.clip(slope_deg, 0, 90)
    
    def _calculate_aspect(self, pixel_size):
        """Aspect (bakı) hesaplama"""
        grad_x = np.gradient(self.dem_data, pixel_size, axis=1)
        grad_y = np.gradient(self.dem_data, pixel_size, axis=0)
        aspect_rad = np.arctan2(-grad_y, grad_x)
        aspect_deg = (np.degrees(aspect_rad) + 360) % 360
        return aspect_deg
    
    def _calculate_hillshade(self, azimuth=315, altitude=45):
        """Hillshade (gölgeleme) hesaplama"""
        azimuth_rad = np.radians(azimuth)
        altitude_rad = np.radians(altitude)
        grad_x, grad_y = np.gradient(self.dem_data)
        slope_rad = np.arctan(np.sqrt(grad_x**2 + grad_y**2))
        aspect_rad = np.arctan2(-grad_y, grad_x)
        hillshade = (np.sin(altitude_rad) * np.cos(slope_rad) + 
                    np.cos(altitude_rad) * np.sin(slope_rad) * 
                    np.cos(azimuth_rad - aspect_rad))
        hillshade = np.clip(hillshade * 255, 0, 255)
        return hillshade.astype(np.uint8)
    
    def create_ultra_realistic_3d(self, sample_rate=3, quality='high'):
        """Ultra gerçekçi 3D model oluştur"""
        print("🎨 Ultra gerçekçi 3D model oluşturuluyor...")
        dem_sampled = self.dem_data[::sample_rate, ::sample_rate]
        slope_sampled = self.slope_data[::sample_rate, ::sample_rate]
        hillshade_sampled = self.hillshade_data[::sample_rate, ::sample_rate]
        height, width = dem_sampled.shape
        x = np.linspace(0, width-1, width)
        y = np.linspace(0, height-1, height)
        colors = self._generate_realistic_colors(dem_sampled, slope_sampled, hillshade_sampled)
        
        surface = go.Surface(
            z=dem_sampled, x=x, y=y, surfacecolor=colors,
            colorscale=self._create_topographic_colorscale(), showscale=True,
            colorbar=dict(
                title="Yükseklik (m)", # DÜZELTİLDİ: 'title' dict içinde olmamalı
                tickmode="linear",
                tick0=np.nanmin(dem_sampled),
                dtick=(np.nanmax(dem_sampled) - np.nanmin(dem_sampled)) / 10,
                len=0.7, thickness=15
            ),
            lighting=dict(ambient=0.3, diffuse=0.8, specular=0.2, roughness=0.1, fresnel=0.2),
            lightposition=dict(x=100, y=200, z=300),
            hovertemplate='<b>Bölge</b><br>Konum: (%{x:.0f}, %{y:.0f})<br>Yükseklik: %{z:.0f} m<br><extra></extra>'
        )
        fig = go.Figure(data=[surface])
        fig.update_layout(
            title=dict(text='🏔️ Ultra Gerçekçi 3D Topografik Model', x=0.5, font=dict(size=20, family='Arial Black')),
            scene=dict(
                xaxis=dict(title='Doğu-Batı Ekseni', showgrid=True, gridcolor='rgba(255,255,255,0.2)', backgroundcolor='rgba(0,0,0,0)', showbackground=True),
                yaxis=dict(title='Kuzey-Güney Ekseni', showgrid=True, gridcolor='rgba(255,255,255,0.2)', backgroundcolor='rgba(0,0,0,0)', showbackground=True),
                zaxis=dict(title='Yükseklik (m)', showgrid=True, gridcolor='rgba(255,255,255,0.2)', backgroundcolor='rgba(0,0,0,0)', showbackground=True),
                bgcolor='rgba(0,0,0,0.1)',
                camera=dict(eye=dict(x=1.8, y=1.8, z=1.2), center=dict(x=0, y=0, z=0), up=dict(x=0, y=0, z=1)),
                aspectratio=dict(x=1, y=1, z=0.3), aspectmode='manual'
            ),
            width=1400, height=900, margin=dict(l=0, r=0, t=50, b=0),
            paper_bgcolor='rgba(0,0,0,0.9)', plot_bgcolor='rgba(0,0,0,0.9)'
        )
        filename = f'bolge_ultra_realistic_{quality}.html'
        pyo.plot(fig, filename=filename, auto_open=True)
        print(f"✅ Ultra gerçekçi model kaydedildi: {filename}")
        return fig
    
    def _generate_realistic_colors(self, dem, slope, hillshade):
        height_norm = (dem - np.nanmin(dem)) / (np.nanmax(dem) - np.nanmin(dem))
        slope_norm = slope / 90.0
        hillshade_norm = hillshade / 255.0
        color_index = height_norm * 0.6 + slope_norm * 0.2 + hillshade_norm * 0.2
        return color_index
    
    def _create_topographic_colorscale(self):
        return[
        [0.0,  '#1b5e20'],  # Düşük rakım (Koyu, Canlı Yeşil)
        [0.2,  '#f9a825'],  # Alt-orta rakım (Belirgin Sarı)
        [0.4,  '#ef6c00'],  # Orta rakım (Güçlü Turuncu)
        [0.6,  '#c62828'],  # Yüksek rakım (Koyu Kırmızı)
        [0.8,  '#4e342e'],  # Zirve altı kayalıklar (Çok Koyu Kahve/Bordo)
        [1.0,  '#ffffff']   # Zirve, kar (Tam Beyaz)
    ]
    
    def create_professional_analysis(self, sample_rate=4):
        print("📊 Profesyonel analiz dashboard'u oluşturuluyor...")
        dem_sampled = self.dem_data[::sample_rate, ::sample_rate]
        slope_sampled = self.slope_data[::sample_rate, ::sample_rate]
        aspect_sampled = self.aspect_data[::sample_rate, ::sample_rate]
        hillshade_sampled = self.hillshade_data[::sample_rate, ::sample_rate]
        height, width = dem_sampled.shape
        x, y = np.linspace(0, width-1, width), np.linspace(0, height-1, height)
        
        fig = make_subplots(rows=2, cols=2, subplot_titles=['3D Topografik Model', 'Eğim Analizi (3D)', 'Bakı Analizi (3D)', 'Gölgeleme Analizi (3D)'],
                            specs=[[{'type': 'scene'}, {'type': 'scene'}], [{'type': 'scene'}, {'type': 'scene'}]],
                            vertical_spacing=0.08, horizontal_spacing=0.05)
        
        fig.add_trace(go.Surface(z=dem_sampled, x=x, y=y, colorscale='terrain', showscale=False, name='Topografya'), row=1, col=1)
        fig.add_trace(go.Surface(z=dem_sampled, x=x, y=y, surfacecolor=slope_sampled, colorscale='Reds', showscale=True, colorbar=dict(x=0.48, len=0.4, title='Eğim (°)')), row=1, col=2)
        fig.add_trace(go.Surface(z=dem_sampled, x=x, y=y, surfacecolor=aspect_sampled, colorscale='HSV', showscale=True, colorbar=dict(x=0.02, len=0.4, title='Bakı (°)')), row=2, col=1)
        fig.add_trace(go.Surface(z=dem_sampled, x=x, y=y, surfacecolor=hillshade_sampled, colorscale='gray', showscale=True, colorbar=dict(x=1.02, len=0.4, title='Gölgeleme')), row=2, col=2)
        
        fig.update_layout(title=dict(text='Profesyonel Jeomorfolojik Analiz', x=0.5, font=dict(size=18, family='Arial Black')),
                          height=1000, width=1600, showlegend=False, paper_bgcolor='white')
        
        camera_settings = dict(eye=dict(x=1.5, y=1.5, z=1.2), center=dict(x=0, y=0, z=0))
        for i in range(1, 5):
            scene_name = f'scene{i if i > 1 else ""}'
            fig.update_layout(**{scene_name: dict(camera=camera_settings, aspectratio=dict(x=1, y=1, z=0.3), aspectmode='manual')})
        
        filename = 'bolge_profesyonel_analiz.html'
        pyo.plot(fig, filename=filename, auto_open=True)
        print(f"✅ Profesyonel analiz kaydedildi: {filename}")
        return fig
    
    def create_cinematic_flythrough(self, sample_rate=5, duration=20):
        print("🎬 Sinematik uçuş animasyonu oluşturuluyor...")
        dem_sampled = self.dem_data[::sample_rate, ::sample_rate]
        colors = self._generate_realistic_colors(
            dem_sampled, self.slope_data[::sample_rate, ::sample_rate], self.hillshade_data[::sample_rate, ::sample_rate])
        height, width = dem_sampled.shape
        x, y = np.linspace(0, width-1, width), np.linspace(0, height-1, height)
        n_frames = duration * 2
        frames = []
        for i in range(n_frames):
            t = i / n_frames
            angle, radius, height_factor = t * 4 * np.pi, 3 - 1.5 * t, 2 - 1.5 * t
            eye_x, eye_y, eye_z = radius * np.cos(angle), radius * np.sin(angle), height_factor
            frames.append(go.Frame(layout=dict(scene=dict(camera=dict(eye=dict(x=eye_x, y=eye_y, z=eye_z), center=dict(x=0, y=0, z=0.3)))), name=f'frame_{i}'))
        
        fig = go.Figure(
            data=[go.Surface(z=dem_sampled, x=x, y=y, surfacecolor=colors, colorscale=self._create_topographic_colorscale(), showscale=True,
                             colorbar=dict(title="Yükseklik (m)"), # DÜZELTİLDİ
                             lighting=dict(ambient=0.2, diffuse=0.9, specular=0.3, roughness=0.05))],
            frames=frames)
        
        fig.update_layout(
            title='🎬 Sinematik Uçuş', scene=dict(aspectratio=dict(x=1, y=1, z=0.3), aspectmode='manual', bgcolor='rgba(0,0,0,0.9)'),
            updatemenus=[{'type': 'buttons', 'showactive': False, 'y': 0.9, 'x': 0.1,
                          'buttons': [{'label': '🎬 Filmi Başlat', 'method': 'animate', 'args': [None, {'frame': {'duration': 500, 'redraw': True}, 'fromcurrent': True, 'transition': {'duration': 100}}]},
                                      {'label': '⏸️ Duraklat', 'method': 'animate', 'args': [[None], {'frame': {'duration': 0}}]}]}],
            width=1400, height=900, paper_bgcolor='black')
        
        filename = 'bolge_cinematic.html'
        pyo.plot(fig, filename=filename, auto_open=True)
        print(f"✅ Sinematik animasyon kaydedildi: {filename}")
        return fig
    
    def generate_report(self):
        """Analiz raporu oluştur"""
        print("\n" + "="*60)
        print("📊 3D ARAZİ ANALİZ RAPORU")
        print("="*60)
        
        print(f"🗻 Veri Boyutu: {self.dem_data.shape}")
        print(f"📏 Min Yükseklik: {np.nanmin(self.dem_data):.2f} m")
        print(f"📏 Max Yükseklik: {np.nanmax(self.dem_data):.2f} m")
        print(f"📏 Ortalama Yükseklik: {np.nanmean(self.dem_data):.2f} m")
        print(f"📐 Ortalama Eğim: {np.nanmean(self.slope_data):.2f}°")
        print(f"📐 Max Eğim: {np.nanmax(self.slope_data):.2f}°")
        
        slope_classes = {
            'Düz (0-5°)': np.sum((self.slope_data >= 0) & (self.slope_data < 5)),
            'Hafif (5-15°)': np.sum((self.slope_data >= 5) & (self.slope_data < 15)),
            'Orta (15-30°)': np.sum((self.slope_data >= 15) & (self.slope_data < 30)),
            'Dik (30-45°)': np.sum((self.slope_data >= 30) & (self.slope_data < 45)),
            'Çok Dik (>45°)': np.sum(self.slope_data >= 45)
        }
        total_pixels = np.sum(~np.isnan(self.slope_data))
        
        print("\n🎯 EĞİM SINIFLANDIRMASI:")
        for class_name, count in slope_classes.items():
            percentage = (count / total_pixels) * 100
            # --- EKSİK KISIM TAMAMLANDI ---
            print(f"  - {class_name:<20}: {percentage:>7.2f} %")
            
        print("="*60)


# --- KODU ÇALIŞTIRMAK İÇİN ANA BLOK ---

if __name__ == '__main__':
    # Kullanacağınız DEM dosyasının adını buraya yazın
    # Bu dosyanın, Python kodunuzla aynı klasörde olduğundan emin olun!
    dem_dosyasi = 'dem_verisi.tif'

    if not os.path.exists(dem_dosyasi):
        print(f"HATA: '{dem_dosyasi}' dosyası bulunamadı. Lütfen dosya adını kontrol edin.")
    else:
        # Analiz sınıfından bir nesne oluştur
        arazi_analizi = AgriDagi3D(dem_path=dem_dosyasi)

        # İstatistiksel raporu konsola yazdır
        arazi_analizi.generate_report()

        # Çalıştırmak istediğiniz analiz fonksiyonunu seçin.
        # Aynı anda birden fazlasını çalıştırmak sisteminizi yorabilir.
        # İstediğinizin başındaki '#' işaretini kaldırarak çalıştırabilirsiniz.
        
        # 1. Ultra Gerçekçi 3D Model
        arazi_analizi.create_ultra_realistic_3d(sample_rate=2)
        
        # 2. Profesyonel Analiz Paneli
        # arazi_analizi.create_professional_analysis(sample_rate=4)

        # 3. Sinematik Uçuş Animasyonu
        # arazi_analizi.create_cinematic_flythrough(sample_rate=4, duration=15)
