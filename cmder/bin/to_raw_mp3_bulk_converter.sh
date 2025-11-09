# #!/bin/bash

# # === CONFIG ===
# SRC_DIR="../holyquran"     
# DST_DIR="./holyquran"  
     
# # === LOOP ===
# for file in "$SRC_DIR"/*.mp3; do
#     # skip if no mp3s found
#     [ -e "$file" ] || continue

#     base=$(basename "$file" .mp3)
#     out="$DST_DIR/$base.pcm"

#     echo "Converting: $file → $out"
#     ffmpeg -y -i "$file" -f s16le -ar 48000 -ac 2 "$out"
# done

# echo "✅ All done! PCM files are in: $DST_DIR"
#!/bin/bash

echo "🎵 MP3 → PCM Converter"
echo "----------------------"

# === ASK USER FOR PATHS ===
read -rp "Enter source directory (with .mp3 files): " SRC_DIR
read -rp "Enter destination directory for .pcm files: " DST_DIR

# === VALIDATION ===
if [ ! -d "$SRC_DIR" ]; then
    echo "❌ Source directory not found: $SRC_DIR"
    exit 1
fi

mkdir -p "$DST_DIR"  

echo "🔄 Converting from: $SRC_DIR"
echo "📂 Output to:       $DST_DIR"
echo "----------------------"

# === LOOP ===
shopt -s nullglob  # avoid literal *.mp3 if no matches
for file in "$SRC_DIR"/*.mp3; do
    base=$(basename "$file" .mp3)
    out="$DST_DIR/$base.pcm"

    echo "🎧 Converting: $base.mp3 → $base.pcm"
    ffmpeg -y -i "$file" -f s16le -ar 48000 -ac 2 "$out"

    if [ $? -eq 0 ]; then
        echo "✅ Done: $out"
    else
        echo "⚠️ Failed to convert: $file"
    fi
    echo "----------------------"
done

echo "🏁 All conversions finished! ✅ PCM files saved in: $DST_DIR"
read -rp "Press any key to exit..."