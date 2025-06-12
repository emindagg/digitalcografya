import rasterio
import matplotlib.pyplot as plt
import numpy as np

# --- AYARLAR ---
# İndirdiğiniz GeoTIFF dosyasının adını buraya yazın
# ÖNEMLİ: Bu dosyanın, Python kodunuzla aynı klasörde olduğundan emin olun!
dem_dosyasi = 'dem_verisi.tif'  # KENDİ DOSYA ADINIZLA DEĞİŞTİRİN

# Haritanızın görünümünü özelleştirmek için bu ayarları değiştirebilirsiniz
kontur_sayisi = 15           # Siyah izohips çizgilerinin sayısı
renk_paleti = 'terrain'      # Renk paleti. Diğer seçenekler: 'gist_earth', 'viridis', 'plasma', 'jet'
harita_basligi = 'Bölgenin İzohips Haritası'

# 2. DEM verisini oku
try:
    with rasterio.open(dem_dosyasi) as src:
        elevation = src.read(1)
        nodata = src.nodata
        if nodata is not None:
            elevation = np.ma.masked_equal(elevation, nodata)
        bounds = src.bounds
        extent = [bounds.left, bounds.right, bounds.bottom, bounds.top]

except FileNotFoundError:
    print(f"HATA: '{dem_dosyasi}' adında bir dosya bulunamadı.")
    print("Lütfen dosya adını kontrol edin ve dosyanın kodla aynı klasörde olduğundan emin olun.")
    exit()
except Exception as e:
    print(f"Bir hata oluştu: {e}")
    exit()

# 3. Haritayı çizmeye başla
fig, ax = plt.subplots(figsize=(12, 10))

# X ve Y koordinatları için bir grid oluşturalım (contour ve contourf için gerekli)
x = np.linspace(extent[0], extent[1], elevation.shape[1])
y = np.linspace(extent[2], extent[3], elevation.shape[0])
X, Y = np.meshgrid(x, y)

# 4. Arka planı pürüzsüz bir şekilde renklendir (YENİ YÖNTEM)
# contourf fonksiyonu, yumuşak renk geçişleri oluşturur.
# levels sayısını yüksek tutarak (örn. 100) pürüzsüzlüğü artırıyoruz.
image = ax.contourf(X, Y, elevation, levels=100, cmap=renk_paleti)

# 5. İzohips (kontur) çizgilerini çiz
# Bu kısım aynı kalıyor
konturlar = ax.contour(X, Y, elevation, levels=kontur_sayisi, colors='black', linewidths=0.5)

# 6. İzohips çizgilerinin üzerine yükseklik değerlerini yazdır
ax.clabel(konturlar, inline=True, fontsize=8, fmt='%1.0f m')

# 7. Renk skalası (Colorbar) ekle (GÜNCELLENDİ)
# Artık colorbar'ı imshow'dan değil, contourf'den oluşturulan 'image' değişkeninden alıyoruz.
cbar = fig.colorbar(image, ax=ax, shrink=0.7, orientation='vertical', label='Yükseklik (metre)')

# 8. Haritaya başlık ve eksen etiketleri ekle
ax.set_title(harita_basligi, fontsize=16, fontweight='bold')
ax.set_xlabel('Boylam (Longitude)')
ax.set_ylabel('Enlem (Latitude)')

# Haritanın en-boy oranını koru
ax.set_aspect('equal', adjustable='box')

# 9. Haritayı göster
plt.show()

print("Pürüzsüz harita başarıyla oluşturuldu!")
