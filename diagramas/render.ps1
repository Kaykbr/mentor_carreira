# Renderiza todos os diagramas Mermaid (.mmd) desta pasta em PNG e SVG.
#
# Uso (PowerShell, a partir da raiz do projeto ou desta pasta):
#   ./diagramas/render.ps1
#
# Requisitos: Node.js + npm (usa o mermaid-cli via npx, sem instalacao global).
# A primeira execucao baixa o Chromium do Puppeteer (pode demorar um pouco).

$ErrorActionPreference = "Stop"
$dir = $PSScriptRoot

Write-Host "Renderizando diagramas em: $dir"

Get-ChildItem -Path $dir -Filter *.mmd | ForEach-Object {
    $base = $_.BaseName
    $src  = $_.FullName
    $png  = Join-Path $dir "$base.png"
    $svg  = Join-Path $dir "$base.svg"

    Write-Host "  -> $base (.png + .svg)"
    # PNG: fundo branco e escala 2x para boa resolucao em documentos
    npx -y @mermaid-js/mermaid-cli -i $src -o $png -b white -s 2
    # SVG: vetorial, ideal para a monografia
    npx -y @mermaid-js/mermaid-cli -i $src -o $svg -b white
}

Write-Host "Concluido."
