<<<<<<< Updated upstream
pkgname=adhan-live
pkgver=1.0.0
pkgrel=1
pkgdesc="A simple Adhan reminder script"
url="https://github.com/enzoxwashere/Adhan-Live"
license=('MIT')
arch=('any')
depends=('python')
source=("https://raw.githubusercontent.com/enzoxwashere/Adhan-Reminder/main/adhan-live.py"
        "https://raw.githubusercontent.com/enzoxwashere/Adhan-Reminder/main/a1.mp3")
sha256sums=('SKIP' 'SKIP')

package() {
    install -Dm755 adhan-live.py "$pkgdir/usr/bin/adhan-live"
    install -Dm644 a1.mp3 "$pkgdir/usr/share/adhan-reminder/a1.mp3"
=======
# Maintainer: Enzo <contact@enzox.online>
pkgname=adhan-live
pkgver=2.0.0
pkgrel=1
pkgdesc="عرض احترافي لأوقات الصلاة بواجهة TUI جميلة في الطرفية"
arch=('any')
url="https://github.com/enzoxwashere/adhan-live"
license=('MIT')
depends=(
    'python>=3.9'
    'python-requests'
    'python-rich'
    'libnotify'
)
optdepends=(
    'mpv: مشغل صوت موصى به'
    'ffmpeg: مشغل صوت بديل'
    'mpg123: مشغل صوت بديل'
)
conflicts=('adhan-reminder')
replaces=('adhan-reminder')
provides=('adhan-live')
install=${pkgname}.install
source=(
    "adhan-live.py"
    "a1.mp3"
    "README.md"
    "LICENSE"
)
sha256sums=('SKIP' 'SKIP' 'SKIP' 'SKIP')

package() {
    # Install main script
    install -Dm755 "${srcdir}/adhan-live.py" "${pkgdir}/usr/bin/adhan-live"
    
    # Install audio file
    install -Dm644 "${srcdir}/a1.mp3" "${pkgdir}/usr/share/adhan-live/a1.mp3"
    
    # Install documentation
    install -Dm644 "${srcdir}/README.md" "${pkgdir}/usr/share/doc/${pkgname}/README.md"
    install -Dm644 "${srcdir}/LICENSE" "${pkgdir}/usr/share/licenses/${pkgname}/LICENSE"
>>>>>>> Stashed changes
}
