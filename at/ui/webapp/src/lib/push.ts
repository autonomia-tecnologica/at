// push — a inscrição do navegador no Web Push, que é a notificação do AT.
//
// O AT não tem mais ntfy: a notificação é a do PRÓPRIO PWA, entregue pelo push
// service do navegador (FCM no Chrome/Android, Mozilla no Firefox). O que este
// módulo faz é o lado DA PÁGINA do protocolo: pedir a chave pública do VAPID ao
// servidor, inscrever o `pushManager` com ela, e mandar a inscrição de volta.
// Quem cifra e envia é o servidor (`at/core/push.py`), e quem desenha a
// notificação é o service worker (`/sw.js`).

import { api, post } from "./api";

const KEY_ROUTE = "/api/push/key";
const SUBSCRIBE_ROUTE = "/api/push/subscribe";

export type PushState = NotificationPermission | "unsupported" | "on";

// O navegador sabe fazer push? Um navegador sem service worker, sem
// PushManager ou sem Notification é um navegador para quem este arquivo não
// muda nada — e a tela diz isso, em vez de oferecer um botão que não funciona.
export function supported(): boolean {
  return (
    "serviceWorker" in navigator &&
    "PushManager" in window &&
    "Notification" in window
  );
}

export function state(): PushState {
  if (!supported()) return "unsupported";
  return Notification.permission === "granted" ? "on" : Notification.permission;
}

// A chave vem base64url (a `applicationServerKey` quer BYTES, não texto).
function bytes(key: string): Uint8Array {
  const pad = "=".repeat((4 - (key.length % 4)) % 4);
  const raw = atob((key + pad).replace(/-/g, "+").replace(/_/g, "/"));
  const out = new Uint8Array(raw.length);
  for (let i = 0; i < raw.length; i += 1) out[i] = raw.charCodeAt(i);
  return out;
}

// A inscrição em si: a existente, ou uma nova, e a ida ao servidor. Idempotente
// — reafirmar uma inscrição já feita é o que mantém o servidor com o endpoint
// certo depois de uma rotação do push service.
async function subscribe(): Promise<void> {
  const registration = await navigator.serviceWorker.ready;
  let existing = await registration.pushManager.getSubscription();
  if (!existing) {
    const { key } = await api<{ key: string }>(KEY_ROUTE);
    existing = await registration.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: bytes(key),
    });
  }
  await post(SUBSCRIBE_ROUTE, existing.toJSON());
}

// No carregamento da página: se a permissão JÁ foi dada numa visita anterior,
// reafirma a inscrição sem perguntar nada. Sem permissão, não faz nada — quem
// pergunta é o botão das Configurações, que tem o gesto que a pergunta exige.
export async function register(): Promise<void> {
  if (!supported() || Notification.permission !== "granted") return;
  try {
    await subscribe();
  } catch (error) {
    // Melhor esforço: uma inscrição que não pôde ser reafirmada não derruba a
    // página — o botão continua ali para tentar de novo.
  }
}

// O botão das Configurações: pede a permissão (a do navegador exige um gesto, e
// é por isso que isto não roda sozinho) e inscreve. `true` quando o navegador
// passou a receber os avisos.
export async function enable(): Promise<boolean> {
  if (!supported()) return false;
  const permission = await Notification.requestPermission();
  if (permission !== "granted") return false;
  try {
    await subscribe();
    return true;
  } catch (error) {
    return false;
  }
}
