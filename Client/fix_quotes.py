import sys

file_path = 'd:/GuardianStar/Client/src/main/java/com/example/guardianstar/ui/MainActivity.kt'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace curly quotes with straight quotes
content = content.replace('"', '"').replace('"', '"')

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Fixed quotes in MainActivity.kt")
