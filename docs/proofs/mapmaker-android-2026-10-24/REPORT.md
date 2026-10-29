# Android VM installation — result

**Status:** SDK and Android15 VM installed; Android browser validation blocked on this host. **DAD-M:** Deploy complete for installation, Monitor failed for usable software boot. Product source remained read-only.

Installed official Android command-line tools23.0, emulator37.2.12, platform-tools37.0.1 and Google APIs Android15/API35 x86_64 image revision9. SDK: `/opt/roll-drauf-android/sdk`. AVD: `RollDrauf_API35` under `/home/admin/.local/share/roll-drauf-android/avd/`. Phone profile:780×1688 pixels,320dpi,3GB RAM,2virtualCPUs. The launcher is `/opt/roll-drauf-android/start-vm.py`; checked-in copy, config and versions are retained alongside this report. A missing X11 bridge library was extracted into the installation’s private `runtime-libs` directory; no system package installation was required.

The host exposes neither `/dev/kvm` nor vmx/svm CPU flags. The emulator’s acceleration check reports `KVM requires a CPU that supports vmx or svm`. Google documents [Linux KVM requirements](https://developer.android.com/studio/run/emulator-acceleration) and marks the available [`-accel off` software mode](https://developer.android.com/studio/run/emulator-commandline) as unsupported and very slow. The first boot was therefore attempted explicitly with `ANDROID_I_WANT_MY_TCG=yes`, SwiftShader graphics and localhost-only management ports.

**Verified:** the VM kernel runs, ADB connects, the guest reports Android15/API35, and system packages—including Chrome124.0.6367.219—are installed. Package and activity services became available. Forwarding to a disposable local Flask test app was configured; its actual CSP/security headers were checked from the host.

**Failed:** the software run never set `sys.boot_completed=1` or reached a usable browser. Zygote was killed/restarted around guest seconds1179 and1556, with watchdog-context diagnostics in the kernel log. Chrome’s implicit launch intent could not resolve; its explicit component launch returned `Broken pipe (32)` from the activity service. After1679seconds in the instrumented attempt, the repeated framework restarts made this unsuitable for mobile tests. The task-owned VM, boot monitors, temporary forwards and disposable Flask server were stopped. SDK/AVD data remain installed. The native screenshot is black during incomplete boot; it is not evidence of the mapmaker running.

**Not verified:** the mapmaker mobile view in Android, Android touch/edit/save journeys, or penetration tests. The VM installation does not close the previous security gap or the mobile V3 finding. This failure occurs before the mapmaker loads and is not reported as an application defect. The host constraint and unsupported software mode are consistent with the observed failure; no precise root-cause claim is made beyond the recorded diagnostics.

## Next action

Expose CPU virtualization and `/dev/kvm` to this executor, with read/write access for `admin`, or use an existing KVM-capable development host. Installing a KVM package alone cannot supply CPU extensions hidden by the hypervisor. Verify acceleration, then start the installed profile:

```bash
runuser -u admin -- /opt/roll-drauf-android/sdk/emulator/emulator -accel-check
/opt/roll-drauf-android/start-vm.py --accel on
```

The launcher selects acceleration automatically by default; `--accel off` retains the diagnosed software fallback. `--help` lists the choices. Do not repeat the software boot expecting dependable test performance on this host.

After a successful boot, run the retained `flask-preview.py` with the prepared test Python, set `adb reverse tcp:8766 tcp:8766`, and open `http://127.0.0.1:8766/static/mapmaker/index.html` in Android Chrome. Browser CDP can be forwarded with `adb forward tcp:9222 localabstract:chrome_devtools_remote`, following [Chrome’s Android debugging reference](https://developer.chrome.com/docs/devtools/remote-debugging/). Keep these ports local. Then capture a real Android mapmaker screenshot and run the mobile journey/visibility checks before making any acceptance claim.

**Evidence:** `results.json`, `installed-versions.json`, `install-result.json`, `avd-config.ini`, `logs/` and the setup/launcher scripts. Logs omit authentication-key lines. The preexisting repository baseline is unchanged (see exact file count in results). No production data or account login was used.
