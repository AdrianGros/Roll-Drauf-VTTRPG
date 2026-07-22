# DAD-M Monitor: Access Gate and Book Scene V2

Date: 2026-04-01
Phase: MONITOR
Status: active

## What To Watch

- registration without key should now fail consistently
- valid key registration should still succeed on both signup and register flows
- login success should remain inside the book scene and reveal the dashboard pilot
- reduced-motion users should see a direct state switch without decorative motion reliance
- direct `/dashboard` visits will still differ from the pilot until the scene architecture expands

## Fast Regression Checks

- try creating an account without `registration_key`
- create an account with a valid key
- login with the new account and confirm the in-book dashboard reveal
- click the page-ribbon actions for `Campaigns`, `Characters`, and `Logout`
