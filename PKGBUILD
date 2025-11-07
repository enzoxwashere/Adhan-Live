#Dev: Enzo
pkgname=adhan-reminder
pkgver=1.1.0
pkgrel=1
pkgdesc="Auto Adhan reminder with live console display"
arch=('any')
license=('MIT')
depends=('python' 'python-requests' 'mpg123' 'libnotify')
optdepends=(
    'ffmpeg: alternative audio player'
    'mpv: alternative audio player'
)
source=("adhan-live.py" "a1.mp3")
sha256sums=('SKIP' 'SKIP')

package() {
    # Install main script
    install -Dm755 "${srcdir}/adhan-live.py" "${pkgdir}/usr/bin/adhan-live"
    
    # Install audio file
    install -Dm644 "${srcdir}/a1.mp3" "${pkgdir}/usr/share/adhan-reminder/a1.mp3"
    
    # Create config directory
    install -dm755 "${pkgdir}/etc/adhan-reminder"
}

post_install() {
    echo "Features:"
    echo "  - Beautiful colorful interface"
    echo "  - Live prayer times display"
    echo "  - Countdown timer"
    echo "  - Auto-play adhan at prayer time"
    echo "  - Auto-detect location"
    echo "Adhan Reminder installed successfully!"
    echo "Run: adhan-live"
    echo 
}

post_upgrade() {
    post_install
}
