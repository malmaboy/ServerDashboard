# SSH Checklist

## Safe order

1. Confirm host and environment
2. Check uptime, load, disk, memory
3. Check service status and logs
4. Check listening ports and connectivity
5. Check config files before editing
6. Define rollback before restart or reload

## Read-only first examples

- `hostname`
- `uptime`
- `df -h`
- `free -h`
- `systemctl status <service>`
- `journalctl -u <service> --no-pager -n 100`
