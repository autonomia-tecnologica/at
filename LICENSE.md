# AT — a licença

O AT é **MIT**: qualquer um usa, modifica e redistribui, inclusive fechado, e o
que se pede em troca é este aviso viajar junto.

Os dois artefatos carregam componentes de terceiros, cada um sob a licença do
seu dono. O lugar **único** que declara cada um — o nome, a versão, o
identificador da licença e o caminho do texto — é
`at/vendor/licenses/manifest.json`, e quem diz o que **cada** artefato carrega,
e não o que os dois carregam juntos, é a palavra `license` dele: `at-cli license`
e `at-deploy license`. O artefato é um arquivo só e não tem pasta ao lado para o
aviso morar, então os textos viajam dentro e saem por essa palavra;
`--include-texts` traz o texto inteiro de cada um.

A regra que decide o que pode viajar dentro de um artefato está no §3 —
`docs/pt_BR/rules.md`, "Dependência externa" (e `docs/en_US/rules.md`,
"External dependency"). Este arquivo é a licença; a regra não se repete aqui.

## MIT License

Copyright (c) 2026 Rafael Correia

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
