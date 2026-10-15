#!/usr/bin/env bash
# Free Live Translator — dê dois cliques neste arquivo no Finder.
cd "$(dirname "$0")" || exit 1

if [[ ! -x ".venv/bin/python" ]]; then
  echo "============================================================"
  echo " Free Live Translator - primeira instalação"
  echo " Isso pode levar de 10 a 30 minutos. Não feche esta janela."
  echo " Se pedir a senha do Mac, é para instalar o Homebrew/Python."
  echo "============================================================"
  echo
  if ! FLT_AUTO=1 bash ./setup-macos.sh; then
    echo
    echo "A instalação não terminou. Veja as mensagens acima."
    read -r -p "Pressione Enter para fechar."
    exit 1
  fi
fi

echo
echo "Iniciando... o painel abre sozinho no navegador em alguns segundos."
echo "Para encerrar, feche esta janela."
echo
chmod +x ./start-macos.sh 2>/dev/null
./start-macos.sh
