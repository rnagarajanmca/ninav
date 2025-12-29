#!/bin/bash
# Package GPU worker files for transfer to Windows

echo "📦 Packaging GPU worker files for Windows..."

# Create package directory
PACKAGE_DIR="gpu_worker_package"
rm -rf $PACKAGE_DIR
mkdir -p $PACKAGE_DIR

# Copy necessary files
cp main.py $PACKAGE_DIR/
cp requirements.txt $PACKAGE_DIR/
cp README.md $PACKAGE_DIR/
cp WINDOWS_SETUP.md $PACKAGE_DIR/

# Create ZIP archive
zip -r gpu_worker_package.zip $PACKAGE_DIR/

# Cleanup
rm -rf $PACKAGE_DIR

echo "✅ Package created: gpu_worker_package.zip"
echo ""
echo "📋 Next steps:"
echo "1. Transfer gpu_worker_package.zip to your Windows machine"
echo "2. Extract on Windows"
echo "3. Follow instructions in WINDOWS_SETUP.md"
echo ""
echo "Transfer methods:"
echo "  - Email to yourself"
echo "  - USB drive"
echo "  - Network share"
echo "  - OneDrive/Dropbox"
