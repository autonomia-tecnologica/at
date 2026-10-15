// events — a escrita na pasta vigiada chega à aba aberta, sem recarregar
// (TASK-128, fatia 2/3). O vigia só despacha (`at/core/vigia.py`); quem
// decide o que fazer com o aviso é este módulo, e o que ele faz é pokar — a
// MESMA releitura que uma escrita local já causa (`views.ts`'s `poke`),
// porque o evento não diz qual arquivo mudou, só que algo mudou.
//
// `EventSource` RECONECTA SOZINHO quando a conexão cai — é o próprio
// protocolo (SSE), e não algo que este módulo precisa reimplementar. E ele
// já ignora toda linha que começa com `:` (o `keep-alive` do servidor): só
// uma linha `data:` chega a `onmessage`.

import { poke } from "./views";

const source = new EventSource("/api/events");
source.onmessage = () => poke();
