#!/bin/bash
# ==========================================
# Script final todo-en-uno para WSL2 + VcXsrv
# Configura entorno y lanza GUI de Electron
# ==========================================

echo "==============================="
echo "Configurando entorno para WSL2"
echo "==============================="

# 1️⃣ Detectar WSL
if grep -qi microsoft /proc/version; then
    echo "WSL detectado ✔"
else
    echo "ATENCIÓN: No se detectó WSL automáticamente, pero puedes continuar si estás seguro de estar en WSL."
fi

# 2️⃣ Configurar DISPLAY para VcXsrv
WIN_IP=$(grep nameserver /etc/resolv.conf | awk '{print $2}')
export DISPLAY=$WIN_IP:0.0
echo "DISPLAY configurado como $DISPLAY"

# 3️⃣ Deshabilitar GPU y sandbox para Electron
export ELECTRON_DISABLE_GPU=1
export ELM_DISABLE_SANDBOX=1
echo "Electron GPU deshabilitado ✔"

# 4️⃣ Actualizar repositorios e instalar librerías necesarias
echo "Instalando dependencias de Linux..."
sudo apt update
sudo apt install -y \
libnss3 libnss3-tools \
libatk-bridge2.0-0t64 libgtk-3-0t64 libxss1 \
libasound2t64 libatk1.0-0t64 libcups2t64 \
libxcomposite1 libxdamage1 libxrandr2 libgbm1 \
libgdk-pixbuf2.0-0 libpango-1.0-0 libx11-xcb1 \
libxtst6 libxfixes3 libxrender1 dos2unix \
xdg-desktop-portal xdg-desktop-portal-gtk curl git build-essential -y

# 5️⃣ Convertir scripts .sh a formato Linux
echo "Convirtiendo scripts a formato Linux..."
if [ -d ./scripts ]; then
    find ./scripts -name "*.sh" -exec dos2unix {} \;
fi

# 6️⃣ Instalar Node.js dependencias
echo "Instalando dependencias de Node.js..."
if [ ! -f package.json ]; then
    echo "Error: package.json no encontrado. Asegúrate de estar en la carpeta correcta."
    exit 1
fi
npm install

# 7️⃣ Instalar Playwright navegadores
npx playwright install

# 8️⃣ Ejecutar GUI
echo "Iniciando GUI de Facebook..."
npm start