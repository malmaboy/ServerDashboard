# Server Checklist

## Investigate in this order

1. Scope and blast radius
2. Service status
3. Logs and recent changes
4. CPU, memory, disk, inode, and network saturation
5. Config drift and dependency failures

## Before changes

- Define rollback.
- Define verification.
- Avoid mixing unrelated fixes in the same change window.
