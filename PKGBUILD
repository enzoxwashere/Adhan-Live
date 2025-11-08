# Maintainer: Enzo <contact@enzox.online>
pkgname=adhan-live
pkgver=2.0.0
pkgrel=1
pkgdesc="Professional Islamic prayer times display with beautiful TUI interface"
arch=('any')
url="https://github.com/enzoxwashere/Adhan-Live"
license=('MIT')
depends=(
    'python>=3.9'
    'python-requests'
    'python-rich'
    'libnotify'
)
optdepends=(
    'mpv: recommended audio player'
    'ffmpeg: alternative audio player'
    'mpg123: alternative audio player'
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
}
