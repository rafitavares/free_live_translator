# Free Live Translator

Legendas e tradução simultânea **ao vivo e 100% locais** para palestras, centros espíritas e apresentações. O público escaneia um QR code, abre uma página no celular pela Wi-Fi do local e escolhe a língua em que quer ler. Não há créditos, assinatura nem envio de áudio para a nuvem.

Este projeto é um fork do [Church Cap](https://github.com/Church-Cap/Live-Church-Captions) (licença MIT, v0.8.0). O Church Cap foi feito para cultos em inglês. Este fork deixa a língua do palestrante configurável, com **português como padrão**, e troca o vocabulário cristão em inglês por vocabulário espírita em português. O README original está em [README.upstream.md](README.upstream.md), e a documentação técnica detalhada continua em `docs/` (em inglês).

## Como funciona

```
microfone / mesa de som
        │
        ▼
 Whisper (local) ── transcreve em português ── glossário corrige termos
        │
        ▼
 tradução local (Argos ou SMaLL-100) ── alemão, inglês, francês, italiano…
        │
        ▼
 página no celular via QR code  ·  telão (/display)  ·  OBS (/obs)
```

## O que mudou em relação ao Church Cap

| Aspecto | Church Cap | Este fork |
|---|---|---|
| Língua do palestrante | Fixa em inglês | `CAPTION_SOURCE_LANGUAGE` (padrão `pt`) |
| Modelos Whisper | Só `.en` (inglês) | Multilíngues (`tiny`, `base`, `small`, `medium`…); os `.en` são trocados automaticamente quando a origem não é inglês |
| Prompt do Whisper | Vocabulário de culto em inglês | Vocabulário espírita em português |
| Correções embutidas | Livros bíblicos em inglês | Termos espíritas (perispírito, desobsessão, Allan Kardec, Joanna de Ângelis…) |
| Pacotes Argos | Só inglês → X | Língua de origem → X; se não houver pacote direto, instala origem → inglês → X (o Argos encadeia sozinho) |
| Tigrínia (OPUS) | Ativo | Desativado quando a origem não é inglês (o modelo só traduz a partir do inglês) |

Com `CAPTION_SOURCE_LANGUAGE=en`, o comportamento volta a ser o do Church Cap original.

## Como usar (dois cliques)

1. Baixe o programa: botão verde **Code → Download ZIP** nesta página e descompacte. Quem usa git pode fazer `git clone https://github.com/rafitavares/free_live_translator.git`.
2. Dê dois cliques no atalho do seu sistema:
   - **Windows:** `Iniciar-Windows.bat`
   - **Mac:** `Iniciar-Mac.command`. Se o Mac bloquear, clique com o botão direito → Abrir. Na primeira vez também pode ser preciso rodar `chmod +x Iniciar-Mac.command` no Terminal.
3. **Na primeira vez**, o atalho instala tudo sozinho: Python, bibliotecas e as línguas mais comuns. Isso precisa de internet e leva de 10 a 30 minutos. Depois disso, o programa funciona offline.
4. O navegador abre e pede para criar a **senha do operador**.
5. Aparece o **painel simples**:
   - escolha o microfone;
   - marque as línguas;
   - clique em **Iniciar tradução**;
   - mostre o QR code ao público.

As outras vezes são só dois cliques no atalho. Para encerrar, feche a janela preta do terminal.

O painel completo, com desempenho, glossário e diagnóstico, fica em **Modo avançado**, no rodapé do painel simples.

Requisitos recomendados: Mac com chip Apple Silicon e 16 GB de RAM, ou PC Windows/Linux com CPU de 6 a 8 núcleos e 16 GB. GPU NVIDIA ajuda bastante. Em computadores sem placa de vídeo, ofereça uma ou duas línguas ao mesmo tempo.

### Instalação manual (terminal)

```bash
bash setup-macos.sh && ./start-macos.sh          # macOS
.\setup-windows.cmd ; .\start-windows.cmd        # Windows (PowerShell)
bash setup-linux.sh && ./start-linux.sh          # Linux
```

### Definir a língua do palestrante

No arquivo `.env`, criado pelo setup:

```
CAPTION_SOURCE_LANGUAGE=pt
WHISPER_MODEL=small
```

Valores aceitos: `pt`, `de`, `en`, `es`, `fr`, `it` e outros códigos ISO de duas letras. Reinicie o programa depois de mudar.

### Instalar as traduções

No painel do operador, em **Languages**, use os botões de instalação. Pelo terminal:

```bash
./scripts/install-translation-models-argos.sh          # alemão, inglês, francês, italiano, espanhol…
./scripts/install-translation-models-argos.sh --all    # todas as línguas alcançáveis a partir do português
./scripts/install-small100-ct2-int8.sh                 # tradutor neural SMaLL-100 (mais línguas, mais natural)
```

A instalação precisa de internet. Depois disso, a tradução roda offline.

## Glossário da sua casa espírita

Edite `config/glossary.csv`. Cada linha tem a forma `como o Whisper escreveu errado,forma correta`:

```
wrong,correct
divaldo pereira,Divaldo Franco
centro espirita luz,Centro Espírita Luz
```

Linhas que começam com `#` são comentários. O arquivo é preservado nas atualizações. As correções embutidas ficam em `app/resources/spiritist_corrections_pt.csv`, e os termos que orientam o Whisper em `app/resources/spiritist_prompt_terms_pt.txt`.

O glossário corrige a **transcrição**, antes da tradução. Ele não controla como cada termo é traduzido.

## Usar com Zoom ou Google Meet

- **Áudio da reunião para o tradutor:** direcione o som com um cabo de áudio virtual (BlackHole no Mac, VB-Cable no Windows) e escolha esse dispositivo como entrada no painel.
- **Legendas para quem está na reunião:** use a saída `/obs` no OBS e transmita como câmera virtual, ou compartilhe a página `/display` na tela.
- Integração direta com a API de legendas da Zoom ainda não existe neste fork.

## Limitações conhecidas

- A tradução automática erra nomes e termos doutrinários. Revise o glossário com palestras reais e não use como substituto de intérprete onde a precisão for crítica.
- O atraso típico é de alguns segundos, e cresce em máquinas sem GPU.
- Parte da interface do operador ainda está em inglês e alguns rótulos dizem "English" (por exemplo, "English Delay"); eles se referem à língua de origem.
- A voz traduzida (TTS) só existe para as línguas dos pacotes do projeto original; alemão e português não estão entre elas.

## Testes

```bash
python -m unittest discover -s tests -p "test_source_language.py"   # testes do fork (português)
CAPTION_SOURCE_LANGUAGE=en python -m unittest discover -s tests     # suíte herdada do Church Cap
```

## Licença e créditos

MIT. Baseado no [Church Cap](https://github.com/Church-Cap/Live-Church-Captions), © 2026 Church Cap contributors. Veja [LICENSE](LICENSE) e [docs/legal/THIRD_PARTY_NOTICES.md](docs/legal/THIRD_PARTY_NOTICES.md) para as licenças dos modelos e dependências.
