# Bug List — pearOS ISO Build System

> Analiză statică completă a tuturor scripturilor și fișierelor de configurare.  
> Ultima actualizare: 2026-06-14

**Legendă:** ✅ Rezolvat | ⚠️ Deschis

---

## CRITIC

### BUG-01 ✅ — `enable_services.sh`: `cd` comentat → symlink-urile se creează în locul greșit
**Fișier:** `pear/airootfs/root/enable_services.sh`  
**Rezolvat:** Fișierul a fost rescris complet ca parte din LOGIC-02. `cd /etc/systemd/system/` este acum activ la linia 6 (cale absolută corectă pentru chroot). Toate directoarele target (`multi-user.target.wants`, `network-online.target.wants`, `sockets.target.wants`, `bluetooth.target.wants`) sunt create explicit cu `mkdir -p`.

---

### BUG-02 ✅ — `services.sh`: `network-online.target.wants/` nu este creat
**Fișier:** `services.sh`  
**Rezolvat:** Adăugat `network-online.target.wants` în apelul `mkdir -p` de la secțiunea NetworkManager, și adăugat `mkdir -p sockets.target.wants` înainte de symlink-urile CUPS. Fișierul este marcat DEPRECATED — funcționalitatea trăiește acum în `enable_services.sh`.

---

### BUG-03 ✅ — `build-binary`: `pacman-key --lsign-key` rulează pe HOST, nu în chroot
**Fișier:** `build-binary`, linia 582  
**Rezolvat:** `pacman-key --lsign-key` a fost mutat în interiorul unui singur apel `arch-chroot bash -c "..."` împreună cu `--recv-keys`.

---

### BUG-04 — `sddm.conf1`: nume de fișier neconvențional
**Fișier:** `pear/airootfs/etc/sddm.conf1`  
**Status:** Intenționat — fișier de debug/referință al dezvoltatorului. Configurația SDDM activă se află în `sddm.conf.d/autologin.conf`.

---

### BUG-05 ✅ — `customize_airootfs.sh`: `rm -rf liquid-gel` șterge directorul greșit
**Fișier:** `pear/airootfs/root/customize_airootfs.sh`, linia 131  
**Rezolvat:** Înlocuit `rm -rf liquid-gel` cu `rm -rf /root/liquid-gel` (cale absolută). Totodată eliminat `sleep 10` inutil de la finalul scriptului.

---

## MAJOR

### BUG-06 ✅ — `customize_airootfs.sh`: permisiuni `0777` pe director de sistem
**Fișier:** `pear/airootfs/root/customize_airootfs.sh`, linia 90  
**Rezolvat:** Schimbat `chmod -R 0777` în `chmod -R 0755`.

---

### BUG-07 ✅ — `sshd_config`: `PermitRootLogin yes` — root SSH activat pe live session
**Fișier:** `pear/airootfs/etc/ssh/sshd_config`, linia 32  
**Rezolvat:** Schimbat `PermitRootLogin yes` în `PermitRootLogin prohibit-password`. Root poate fi accesat prin SSH doar cu cheie publică, nu cu parolă.

---

### BUG-08 ✅ — `build-binary`: `_mksignature()` — variabilă nesetată dacă niciun format de imagine nu există
**Fișier:** `build-binary`  
**Rezolvat:** `airootfs_image_filename` inițializat explicit cu `=""`. Adăugat guard `if [[ -z "${airootfs_image_filename}" ]]` care emite eroare fatală cu mesaj clar înainte de `rm` și `gpg`, în loc să ruleze `rm -f -- ".sig"` cu cale goală.

---

### BUG-09 ✅ — `build-binary`: `_make_boot_on_iso9660()` — copie initramfs non-linux617 involuntar
**Fișier:** `build-binary`  
**Rezolvat:** Eliminat catch-all-ul `initramfs-linux*` și ramura `elif` redundantă. Condiția de copiere este acum `initramfs-linux617*` OR regex `initramfs-6.[0-9]+.*\.img` — ambele explicit, fără a prinde `initramfs-linux-lts`, `initramfs-linux-zen` etc.

---

### BUG-10 ✅ — `build-binary`: `_make_boot_on_iso9660()` — idem pentru vmlinuz
**Fișier:** `build-binary`  
**Rezolvat:** Eliminat catch-all-ul `vmlinuz-linux*` și ramura `elif` redundantă. Condiția de copiere este acum `vmlinuz-linux617*` OR regex `vmlinuz-6.[0-9]+.*` — fără a prinde `vmlinuz-linux-lts`, `vmlinuz-linux-zen` etc. Fix aplicat simultan cu BUG-09 în același bloc refactorizat.

---

### BUG-11 ✅ — `build-binary`: `actual_build()` — `$USER` e `root` când scriptul rulează ca root
**Fișier:** `build-binary`, linia 2020  
**Rezolvat:** Înlocuit `sudo chown $USER:$USER *.iso` cu `chown "${SUDO_USER:-$USER}:${SUDO_USER:-$USER}" ./*.iso 2>/dev/null || true`. Eliminat și `sudo` redundant, adăugat glob safety cu `./`.

---

### BUG-12 ✅ — `build-binary`: `_cleanup_pacstrap_dir()` — variabile neghilimele la `rm -rf`
**Fișier:** `build-binary`, liniile 266–311  
**Rezolvat:** Toate cele 46 de apeluri `rm -rf ${pacstrap_dir}/...` au fost ghilimele corect: `rm -rf "${pacstrap_dir}/..."`. Globurile (ex. `Oxygen*`) au fost separate de variabilă: `"${pacstrap_dir}/usr/share/icons/Oxygen"*`.

---

### BUG-13 ✅ — `build-binary`: `_cleanup_pacstrap_dir()` — `chroot` cu cale relativă `bin/bash`
**Fișier:** `build-binary`, linia 312  
**Rezolvat:** Înlocuit `chroot "${pacstrap_dir}" bin/bash -c "pacman -Sy --noconfirm"` cu `arch-chroot "${pacstrap_dir}" bash -c "pacman -Syy --noconfirm"` (cale standard, forțează re-sync complet cu `-Syy`).

---

### BUG-14 ✅ — `build-binary`: `_make_custom_airootfs()` — build eșuează fără internet
**Fișier:** `build-binary`, liniile 506–517  
**Rezolvat:** Adăugată verificare de conectivitate (`curl -fsS --max-time 10 https://github.com`) cu mesaj de eroare clar înainte de `git clone`. Verificarea `git` disponibil a fost mutată înainte de clone. Restructurat blocul fără `if/else` adânc inutil.

---

### BUG-15 ✅ — `build-binary`: `sed` pe fișierul `setup` al installerului — pattern fragil
**Fișier:** `build-binary`  
**Rezolvat:** Pattern-ul `sed` actualizat de la `s/'linux-headers'/'linux617-headers'/g` (care necesita ghilimele simple exacte) la `s/\blinux-headers\b/linux617-headers/g` (word boundary GNU sed — funcționează indiferent de stilul de ghilimele din fișierul sursă).

---

## MINOR

### BUG-16 ✅ — Meniu principal: opțiunea `3)` lipsește `)` din formatare
**Fișier:** `build-binary`, linia 2191  
**Rezolvat:** Înlocuit `$(magentaprint '3')` cu `$(magentaprint '3)')`.

---

### BUG-17 ✅ — Descriere incorectă pentru opțiunea 5 de compresie
**Fișier:** `build-binary`, liniile 1950, 1979  
**Rezolvat:** Descrierea UI actualizată la „Very small filesize, slower — Pear Slim (zstd level 19)". Comentarul din cod corectat din `xz maximum with large blocks` în `zstd level 19 (Pear Slim)`. Indentarea inconsistentă a fost normalizată.

---

### BUG-18 ✅ — `customize_airootfs.sh`: `sudo` inutil în interiorul chrootului
**Fișier:** `pear/airootfs/root/customize_airootfs.sh`, liniile 62, 69, 74, 75  
**Rezolvat:** Eliminat prefixul `sudo` din toate cele 4 apeluri `pacman-key`.

---

### BUG-19 ✅ — `customize_airootfs.sh`: `sleep` calls inutile
**Fișier:** `pear/airootfs/root/customize_airootfs.sh`, liniile 46, 97, 137  
**Rezolvat:** Eliminate `sleep 5` (linia 46), `sleep 5` (linia 97) și `sleep 10` (linia 137). Total economisit: 20 secunde per build.

---


### BUG-21 ✅ — `build-binary`: `set +u` fără `set -u` corespunzător în `printUSBDevices()`
**Fișier:** `build-binary`, liniile 2080, 2182  
**Rezolvat:** Eliminat `set +u` și `set -u` din ambele funcții. Array-ul `usbDevices` este inițializat explicit (`typeset -a`), deci `set -u` nu cauzează probleme. Totodată corectat `${usbDevices[@]}` în `${usbDevices[*]}` pentru cazul cu mai multe dispozitive (stocate ca string în `$USB`).

---

### BUG-22 ✅ — `build-binary`: `$OUT` neghilimelat în apelul `progtest`
**Fișier:** `build-binary`, linia 2007  
**Rezolvat:** Înlocuit `progtest -v -w $OUT -o . pear` cu `progtest -v -w "$OUT" -o . pear`.

---

### BUG-23 ✅ — `build-binary`: `sudo` redundant în funcții care rulează deja ca root
**Fișier:** `build-binary`, liniile 1889, 1896, 2027  
**Rezolvat:** Eliminat `sudo` din toate cele 3 apeluri `rm -rf ./work/` și actualizat mesajul din `clean_out()`.

---

### BUG-24 ✅ — `_read_profile()`: `pacman_conf` este rezolvat de două ori
**Fișier:** `build-binary`, linia 1524  
**Rezolvat:** Eliminat al doilea apel redundant `pacman_conf="$(realpath -- "${pacman_conf}")"` din blocul `bootstrap_packages`.

---

### BUG-25 ✅ — `cleanup-packages.sh`: nu sincronizează baza de date înainte de verificare
**Fișier:** `cleanup-packages.sh`, linia 20  
**Rezolvat:** Adăugat `pacman -Sy` automat la începutul verificării, cu avertisment non-fatal dacă sincronizarea eșuează.

---

## PROBLEME DE LOGICĂ / DESIGN

### LOGIC-01 ✅ — `customize_airootfs.sh`: remove → reinstall `plasma-welcome` fără verificare versiune
**Rezolvat:** Eliminat pasul `pacman -R plasma-welcome` separat. Instalarea se face acum direct cu `pacman -S --noconfirm --overwrite='*' plasma-welcome`, care suprascrie fișierele conflictuale indiferent de versiunea instalată. Adăugat și `mkdir -p /etc/skel/.config/autostart` pentru a evita o eroare dacă directorul nu există.

---

### LOGIC-02 ✅ — `enable_services.sh` vs `services.sh` — duplicare de funcționalitate cu inconsistențe
**Rezolvat:** `enable_services.sh` a fost rescris complet ca sursă unică de adevăr pentru activarea serviciilor. Acum include toate serviciile din ambele fișiere (Display Manager, NetworkManager, CUPS, Bluetooth, Virtualizare, Power Management), rulează din `/etc/systemd/system/` (fix BUG-01 și BUG-02 incluse), și creează toate directoarele necesare (`network-online.target.wants`, `sockets.target.wants`, `bluetooth.target.wants`). `services.sh` a fost marcat ca **DEPRECATED** cu comentar explicit.

---

### LOGIC-03 ✅ — `build-binary`: curățarea kernel-elor non-linux617 duplicată
**Fișier:** `build-binary`  
**Rezolvat:** Eliminat al doilea bloc `find ... -name "linux*.preset" ! -name "linux617*.preset" -type f -delete` care era identic cu cel de la linia 624. Blocul de la finalul secțiunii (cu comentariul „Also proactively remove") a fost șters.

---

### LOGIC-04 ✅ — `build-binary`: `_run_once` nu este folosit pentru `_make_bootmodes`
**Fișier:** `build-binary`, linia 1708  
**Rezolvat:** Înlocuit apelul direct `_make_bootmodes` cu `_run_once _make_bootmodes`, consistent cu toate celelalte funcții din `_build_iso_base()`. La reluarea unui build, bootmodes deja finalizate sunt sărite prin mecanismul de marker files al `_run_once`.

---

### LOGIC-05 ✅ — `profiledef.sh` modificat fără garanția restaurării la întrerupere
**Fișier:** `build-binary`  
**Rezolvat:** Adăugat `trap 'mv pear/profiledef.sh.backup pear/profiledef.sh 2>/dev/null; trap - EXIT INT TERM' EXIT INT TERM` imediat după backup. Aceasta garantează că `profiledef.sh` este restaurat chiar dacă build-ul este întrerupt cu Ctrl+C, dacă scriptul eșuează, sau dacă procesul primește SIGTERM. Trap-ul este dezactivat explicit după restaurarea normală.

---

## Sumar

| Status | Nr. buguri |
|--------|-----------|
| ✅ Rezolvate | 29 |
| ⚠️ Deschise | 0 |
| — Intenționat (nu bug) | 2 (BUG-04, BUG-20) |

*Generat: 2026-06-14 — Actualizat: 2026-06-14*
