# Regression Debugging

## Debug in this order

1. Repro steps and fixture data
2. Recent code and config changes
3. Test assumptions and environment drift
4. Flakiness signals such as timing, network, or shared state
5. Minimal regression test to lock the fix
