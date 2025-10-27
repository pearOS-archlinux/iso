#!/bin/bash
# cleanup-packages.sh
# Verifică și curăță lista de pachete, eliminând cele care nu mai există în repo-uri

PACKAGES_FILE="packages/packages.x86_64"
BACKUP_FILE="packages/packages.x86_64.backup"

# Verifică dacă fișierul există
if [[ ! -f "$PACKAGES_FILE" ]]; then
    echo -e "[\e[91m%\e[0m] Error: $PACKAGES_FILE not found!"
    exit 1
fi

# Verifică dacă suntem root (pacman -Si necesită sync)
if [ "$(id -u)" -ne 0 ]; then
    echo -e "[\e[93m%\e[0m] Warning: Running without root. Some checks might be inaccurate."
    echo -e "[\e[93m%\e[0m] Consider running: sudo $0"
    echo ""
fi

echo -e "[\e[92m%\e[0m] Creating backup: $BACKUP_FILE"
cp "$PACKAGES_FILE" "$BACKUP_FILE"

echo -e "[\e[92m%\e[0m] Checking packages against repositories..."
echo ""

temp_file=$(mktemp)
valid_count=0
invalid_count=0
comment_count=0

while IFS= read -r line; do
    # Păstrează comentariile și linii goale
    if [[ -z "$line" ]]; then
        echo "$line" >> "$temp_file"
        continue
    fi
    
    if [[ "$line" =~ ^[[:space:]]*# ]]; then
        echo "$line" >> "$temp_file"
        ((comment_count++))
        continue
    fi
    
    # Verifică dacă pachetul există
    package=$(echo "$line" | xargs)  # trim whitespace
    
    if pacman -Si "$package" &> /dev/null; then
        echo "$line" >> "$temp_file"
        echo -e "[\e[92m✓\e[0m] $package"
        ((valid_count++))
    else
        # Comentează în loc să șteargă
        echo "# INVALID: $line" >> "$temp_file"
        echo -e "[\e[91m✗\e[0m] $package (NOT FOUND - commented out)"
        ((invalid_count++))
    fi
done < "$PACKAGES_FILE"

echo ""
echo -e "[\e[94m━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\e[0m"
echo -e "[\e[92m%\e[0m] Summary:"
echo -e "  Valid packages:   \e[92m$valid_count\e[0m"
echo -e "  Invalid packages: \e[91m$invalid_count\e[0m"
echo -e "  Comments/empty:   \e[93m$comment_count\e[0m"
echo -e "[\e[94m━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\e[0m"
echo ""

if [ $invalid_count -eq 0 ]; then
    echo -e "[\e[92m%\e[0m] All packages are valid! No changes needed."
    rm "$temp_file"
else
    echo -e "[\e[93m%\e[0m] Found $invalid_count invalid package(s)."
    read -p "Update $PACKAGES_FILE (invalid packages will be commented)? (y/N): " confirm
    
    if [[ "$confirm" =~ ^[Yy]$ ]]; then
        mv "$temp_file" "$PACKAGES_FILE"
        echo -e "[\e[92m%\e[0m] Updated $PACKAGES_FILE"
        echo -e "[\e[92m%\e[0m] Original backed up to: $BACKUP_FILE"
    else
        rm "$temp_file"
        echo -e "[\e[93m%\e[0m] No changes made."
    fi
fi

echo ""
echo -e "[\e[92m%\e[0m] Done!"

