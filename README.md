# PETase AI Bio-Hub — phone prototype

A working, fully offline phone app for your PETase hackathon project. It runs the same kinetics maths as your notebook,
lets you edit every parameter, analyses real sequences, exports files, and can push a config to an IoT reactor.

> **Honest scope:** every conversion / yield number is a **simulation**. Tm, ΔG and RMSF are values *you* enter from your
> ESM-2 / stability notebook — the phone does not run ESM-2. Nothing here is wet-lab validated.

## What's in the zip

| Path | What it is |
|---|---|
| `index.html` | The whole app in one file (no internet needed). Open it in a phone browser, or it is bundled in the APK. |
| `manifest.webmanifest`, `sw.js`, `icon-*.png` | Make `index.html` installable as a PWA ("Add to Home screen") when hosted over HTTPS. |
| `android-app/` | Android Studio / Gradle project (WebView wrapper with camera, file-picker, save-to-Downloads, LAN POST). |
| `build_apk.sh`, `.github/workflows/build-apk.yml` | Produce `petase-ai.apk` **and** `petase-ai.apk.idsig`. |
| `samples/` | `sample_sequences.fasta`, `sample_reactor_log.csv`, `sample_reactor_config.json` — import them in the app. |
| `pipeline/petase_step9.py` | Your Step 9 cell, fixed and standalone (generates the sample files). |
| `docs/` | 3-slide deck (`.pptx`) and explainer (`.pdf`). |

## Get the APK + .idsig (pick one)

The APK is **not pre-built in this zip** — building needs the Android SDK, which was not available where this package was
generated, and a fake APK would not install. Two reliable ways:

1. **GitHub Actions (no installs):** create a new GitHub repo, upload the *contents* of this folder, open **Actions →
   Build PETase AI APK → Run workflow**. Download the `petase-ai-apk` artifact: `petase-ai.apk` + `petase-ai.apk.idsig`.
2. **Your PC:** install Android Studio (or just JDK 17 + SDK), set `ANDROID_HOME`, run `./build_apk.sh`.
   Or open `android-app/` in Android Studio → *Build ▸ Build APK(s)*.

Install: copy the APK to the phone → open it → allow "install unknown apps". (The `.idsig` is the APK v4 signature used by
`adb install --incremental`; the phone does not need it for a normal install.)
The signing key is a throw-away demo key — fine for a hackathon, **not** for the Play Store.

## Test on your phone right now (no build)

- **Quickest:** send `index.html` to the phone and open it in Chrome. Everything works except the camera
  (Chrome needs HTTPS for camera access).
- **Full PWA:** host the folder on GitHub Pages / Netlify Drop (HTTPS), open the URL in Chrome → ⋮ → *Add to Home screen*.
  Camera and offline caching then work.

## Using the app

1. **Reactor** — ▶ Start run: temperature relaxes to the set-point, PET converts per the kinetics model, chart updates live.
   Change set-point, stir speed, PET load, volume; flip the heater off and watch it cool; log methanol feeds.
   The *Enzyme state* tile compares Tm to the set-point (stable ≥ 3 °C margin, marginal 0–3, denaturing < 0).
2. **Scanner** — camera to photograph the item; pick its ♻ code. Only ♻1 (PET) is a PETase substrate; others are rejected.
   Gives half-conversion time, enzyme mass, 24 h TPA/EG yield. *(Automatic resin recognition is not implemented.)*
3. **Mutator** — paste any sequence → length, mass, GRAVY, net charge, aliphatic index, substitutions vs the wild-type
   fragment. Enter Tm / ΔG / activity from your notebook → **Use in reactor**.
4. **Report** — live report, export FASTA / CSV log / JSON config, share, save runs, import the sample files,
   **Push config** (HTTP POST) to an ESP32/Arduino reactor controller on your Wi-Fi.

## The model (same in `index.html` and `pipeline/petase_step9.py`)

```
k       = 0.045 · (T/55) · activity · stir(rpm) · stability(T, Tm)
X(t)    = min( 100·(1 − e^(−k·t)), 95.2 )      # % conversion
stir    = min(1, √(rpm/200))                    # assumption
stability = 1 if T ≤ Tm else e^(−(T−Tm)/3)     # assumption
TPA (g) = load·volume·X/100 · 166.13/192.17
```
At 60 °C, Tm 61.2 °C, 250 RPM → **69.22 % at 24 h** (identical to your notebook).

## Things I changed from your original code — please read

- Fixed the broken line `conversion = 100.0 * (1.0np.exp …)`.
- Removed `max(61.2, simulated_triad_distance * 17.0)`: it forced the "Tm > 60 °C achieved" result no matter what the
  model produced. Tm is now an explicit input and the report shows the real margin (**+1.2 °C is thin**).
- Wild-type Tm changed from 37 °C to **47 °C** (reported IsPETase values are roughly mid-to-high 40s; edit if you have a source).
  Wild-type relative activity 0.3 is an assumption.
- The old chart's 78.5 % at 24 h disagreed with the 69.2 % card; both now come from the same function.
- The 20-aa sequences are **fragments**; the catalytic triad (Ser160/Asp206/His237) is not inside them.
- Recombinant-enzyme production (Pichia + methanol) is a BSL-1 lab activity, not a kitchen one; "home-scale" here means a small
  bench reactor, and real PET flakes need pre-treatment to approach these conversions.

## Android notes

`MainActivity.java` loads the app from `https://appassets.androidplatform.net/assets/index.html` (secure origin so the camera
works), handles camera permission, the file picker, saving exports to `Downloads/PETaseAI/`, and a native HTTP POST for IoT
pushes (no CORS/mixed-content problems on a LAN). It was written without being compiled in the generation environment —
if Gradle reports an error, it will point at a specific line.
