#!/usr/bin/env bash
#This script runds inside airootfs chroot during build
# it's executed automatically by mkarchiso

set -e -u

echo "==========================="
echo "Customizing pearOS Live env"
echo "==========================="

echo "Setting OS release"
echo "pearOS" > /etc/arch-release && \
	echo "OS release updated" ||\
	echo "Failed to set OS release"

if command -v plymouth-set-default-theme &> /dev/null; then
	echo "Setting plymouth theme"
	plymouth-set-default-theme -R pear-plymouth && \
		echo "Success!" || \
		echo "Failed to set plymouth theme"
else
	echo "Plymouth command theme not found"
fi

echo "Overriding plasma-workspace files with pearos-settings custom patches..."
# Verifică dacă pearos-settings este instalat
if pacman -Q pearos-settings &>/dev/null; then
	# Lista de fișiere care trebuie suprascrise din pearos-settings
	declare -a override_files=(
		"/usr/share/plasma/plasmoids/org.kde.plasma.appmenu/contents/config/config.qml"
		"/usr/share/plasma/plasmoids/org.kde.plasma.appmenu/contents/config/main.xml"
		"/usr/share/plasma/plasmoids/org.kde.plasma.appmenu/contents/ui/MenuDelegate.qml"
		"/usr/share/plasma/plasmoids/org.kde.plasma.appmenu/contents/ui/configGeneral.qml"
		"/usr/share/plasma/plasmoids/org.kde.plasma.appmenu/contents/ui/main.qml"
		"/usr/share/plasma/plasmoids/org.kde.plasma.appmenu/metadata.json"
	)
	
	# Găsește pachetul pearos-settings în cache-ul pacman
	pearos_pkg=$(pacman -Q pearos-settings | awk '{print $1"-"$2}')
	pkg_cache=$(find /var/cache/pacman/pkg -name "${pearos_pkg}*.pkg.tar*" 2>/dev/null | head -1)
	
	if [[ -z "$pkg_cache" || ! -f "$pkg_cache" ]]; then
		# Încearcă să găsească pachetul cu numele complet
		pkg_cache=$(find /var/cache/pacman/pkg -name "pearos-settings-*.pkg.tar*" 2>/dev/null | head -1)
	fi
	
	if [[ -n "$pkg_cache" && -f "$pkg_cache" ]]; then
		# Extrage fișierele din pachet
		temp_dir=$(mktemp -d)
		cd "$temp_dir"
		bsdtar -xf "$pkg_cache" 2>/dev/null || tar -xf "$pkg_cache" 2>/dev/null
		
		for target_file in "${override_files[@]}"; do
			# Caută fișierul în pachetul extras
			if [[ -f ".$target_file" ]]; then
				install -d "$(dirname "$target_file")"
				cp -f ".$target_file" "$target_file" && \
					echo "  ✓ Overridden: $target_file" || \
					echo "  ✗ Failed to override: $target_file"
			else
				echo "  ⚠ File not found in pearos-settings package: $target_file"
			fi
		done
		
		cd - >/dev/null
		rm -rf "$temp_dir"
		echo "Done overriding plasma-workspace files with pearos-settings patches."
	else
		# Dacă pachetul nu este în cache, încercă să extragă fișierele direct din pachetul instalat
		# folosind pacman pentru a obține informații despre pachet
		echo "  ⚠ Package cache not found, trying alternative method..."
		
		# Verifică dacă fișierele există în lista de fișiere a pachetului
		pearos_file_list=$(pacman -Ql pearos-settings 2>/dev/null)
		
		for target_file in "${override_files[@]}"; do
			# Verifică dacă fișierul este în lista de fișiere a pachetului
			if echo "$pearos_file_list" | grep -qF " $target_file$"; then
				# Încearcă să găsească pachetul în toate locațiile posibile
				for cache_dir in /var/cache/pacman/pkg /var/lib/pacman; do
					pkg_file=$(find "$cache_dir" -name "*pearos-settings*.pkg.tar*" 2>/dev/null | head -1)
					if [[ -n "$pkg_file" && -f "$pkg_file" ]]; then
						temp_dir=$(mktemp -d)
						cd "$temp_dir"
						bsdtar -xf "$pkg_file" ".$target_file" 2>/dev/null || tar -xf "$pkg_file" ".$target_file" 2>/dev/null
						if [[ -f ".$target_file" ]]; then
							install -d "$(dirname "$target_file")"
							cp -f ".$target_file" "$target_file" && \
								echo "  ✓ Overridden: $target_file" || \
								echo "  ✗ Failed to override: $target_file"
						fi
						cd - >/dev/null
						rm -rf "$temp_dir"
						break
					fi
				done
			else
				echo "  ⚠ File not found in pearos-settings package list: $target_file"
			fi
		done
		echo "Done overriding plasma-workspace files with pearos-settings patches."
	fi
else
	echo "Warning: pearos-settings package not found, skipping file overrides."
fi

echo "==================="
echo "Script run complete"
echo "==================="
