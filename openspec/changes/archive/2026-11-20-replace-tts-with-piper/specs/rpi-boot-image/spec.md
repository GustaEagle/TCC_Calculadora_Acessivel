## MODIFIED Requirements

### Requirement: TTS offline em português embutido

A imagem SHALL incluir o motor **Piper** (`piper-tts` sobre `onnxruntime`) com a voz **`pt_BR-cadu-medium`** embutida, e a cadeia de áudio necessária para sintetizar voz em **português do Brasil** de forma **offline** (sem qualquer dependência de rede/nuvem), preservando o feedback por voz de entradas e resultados. O `onnxruntime` SHALL vir do repositório do Alpine (`py3-onnxruntime`), e o modelo de voz SHALL ser embutido na imagem com integridade verificada (sha256). O `espeak-ng` SHALL permanecer na imagem como fonemizador do Piper e como motor de **fallback**; o `pyttsx3` SHALL NOT ser exigido.

#### Scenario: Anúncio por voz sem rede

- **WHEN** o dispositivo está sem conexão de rede e o usuário realiza uma operação na calculadora
- **THEN** a entrada e/ou o resultado são anunciados por voz em português do Brasil (voz `cadu`), usando o motor local Piper, sem acessar a rede

#### Scenario: Motor de voz inicializa corretamente

- **WHEN** a aplicação inicia o serviço de TTS na imagem
- **THEN** o modelo `cadu` é carregado a partir da imagem e a síntese ocorre sem falha; se o Piper estiver indisponível, o sistema degrada para `espeak-ng` sem travar a entrada

#### Scenario: Voz embutida e verificada, sem download em execução

- **WHEN** a imagem é construída
- **THEN** o modelo `pt_BR-cadu-medium` (`.onnx` + `.onnx.json`) é incluído com sha256 verificado, e nenhum componente de voz é baixado quando o dispositivo está em uso
