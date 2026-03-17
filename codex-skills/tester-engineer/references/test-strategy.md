# Test Strategy

## Choose test level

- Unit: pure logic and branching
- Integration: module boundaries, DB, file system, external adapters
- Contract/API: request and response behavior
- End-to-end: high-value user journeys
- Smoke: deployment confidence and availability

## Coverage prompts

- Which behavior would be expensive to break again?
- What is the narrowest test that proves the fix?
- Which branches remain untested after the change?
