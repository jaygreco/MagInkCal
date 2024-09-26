## systemd setup and usage

1. Copy the unit file (maginkcal.service) and the timer file (maginkcal.timer) to `/etc/systemd/system`
1. Reload systemd units: `sudo systemctl daemon-reload`
1. Enable the timer (not the service!) with `systemctl enable maginkcal.timer`
1. Start the timer with `systemctl start maginkcal.timer`
