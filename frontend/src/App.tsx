import { FormEvent, useEffect, useMemo, useState } from "react";
import FullCalendar from "@fullcalendar/react";
import dayGridPlugin from "@fullcalendar/daygrid";
import interactionPlugin from "@fullcalendar/interaction";
import timeGridPlugin from "@fullcalendar/timegrid";
import esLocale from "@fullcalendar/core/locales/es";
import type { EventInput } from "@fullcalendar/core";
import {
  BarChart3,
  Bell,
  CalendarDays,
  ChevronDown,
  ChevronRight,
  CircleAlert,
  Clock3,
  FileText,
  Grid2X2,
  ImagePlus,
  Instagram,
  LayoutDashboard,
  Link2,
  List,
  LoaderCircle,
  LogOut,
  Plus,
  Search,
  Send,
  Settings,
  Sparkles,
} from "lucide-react";
import logo from "./assets/relay-logo.png";

const API = "/api/v1";
type Page = "dashboard" | "calendar" | "content" | "connections" | "settings";
type Brand = { id: string; name: string; timezone: string };
type Context = {
  user: { username: string; display_name: string };
  workspace: { id: string; name: string };
  workspaces: Array<{ id: string; name: string; brands: Array<{ id: string; name: string }> }>;
  selected_brand_id: string | null;
  role: string;
  brands: Brand[];
};
type Connection = {
  id: string;
  brand_id: string;
  channel: string;
  display_name: string;
  is_active: boolean;
};
type Post = {
  id: string;
  title: string;
  body: string;
  state: string;
  default_variant_id: string | null;
  updated_at: string;
};
type Publication = {
  id: string;
  channel_connection_id: string;
  scheduled_for: string;
  state: string;
  last_error_message: string;
};
type Summary = {
  published: number;
  scheduled: number;
  failed: number;
  connections: number;
  recent_publications: Array<{
    id: string;
    title: string;
    state: string;
    scheduled_for: string;
    channel: string;
    account: string;
  }>;
  activity: Array<{ date: string; count: number }>;
};

function csrf() {
  return document.cookie
    .split("; ")
    .find((item) => item.startsWith("csrftoken="))
    ?.split("=")[1] ?? "";
}

async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const method = (init.method ?? "GET").toUpperCase();
  const headers = new Headers(init.headers);
  if (init.body && !headers.has("Content-Type")) headers.set("Content-Type", "application/json");
  if (!["GET", "HEAD", "OPTIONS"].includes(method) && csrf()) headers.set("X-CSRFToken", csrf());
  const response = await fetch(`${API}${path}`, { ...init, headers, credentials: "same-origin" });
  if (!response.ok) {
    let message = "No se ha podido completar la operación.";
    try {
      const data = await response.json();
      message = typeof data.detail === "string" ? data.detail : JSON.stringify(data);
    } catch {
      // The upstream response may not contain JSON.
    }
    throw new Error(message);
  }
  return response.status === 204 ? (undefined as T) : response.json();
}

const formatDate = (value: string) =>
  new Intl.DateTimeFormat("es-ES", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
const formatDay = (value: string) =>
  new Intl.DateTimeFormat("es-ES", { weekday: "short", day: "numeric", month: "short" }).format(new Date(value));
const channelName = (channel: string) => (channel.includes("INSTAGRAM") ? "Instagram" : "Facebook");
const initials = (name: string) =>
  name
    .split(" ")
    .map((word) => word[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();

const stateLabels: Record<string, string> = {
  DRAFT: "Borrador",
  PENDING_APPROVAL: "Pendiente de aprobación",
  APPROVED: "Aprobada",
  SCHEDULED: "Programada",
  PUBLISHING: "Publicando",
  PUBLISHED: "Publicada",
  FAILED: "Error",
  CANCELLED: "Cancelada",
};

function State({ value }: { value: string }) {
  const colors: Record<string, string> = {
    DRAFT: "bg-slate-100 text-slate-600",
    PENDING_APPROVAL: "bg-amber-50 text-amber-700",
    APPROVED: "bg-blue-50 text-blue-700",
    SCHEDULED: "bg-violet-50 text-violet-700",
    PUBLISHING: "bg-indigo-50 text-indigo-700",
    PUBLISHED: "bg-emerald-50 text-emerald-700",
    FAILED: "bg-rose-50 text-rose-700",
    CANCELLED: "bg-slate-100 text-slate-500",
  };
  return (
    <span className={`rounded-md px-2 py-1 text-[10px] font-bold uppercase tracking-[.08em] ${colors[value] ?? colors.DRAFT}`}>
      {stateLabels[value] ?? value.replaceAll("_", " ")}
    </span>
  );
}

function BrandMark({ size = "h-10 w-10" }: { size?: string }) {
  return <img src={logo} className={`${size} rounded-xl object-cover shadow-sm`} alt="Relay" />;
}

function Loading({ label = "Cargando datos reales…" }: { label?: string }) {
  return (
    <div className="grid min-h-52 place-items-center rounded-2xl border border-slate-200 bg-white text-sm text-slate-500 shadow-sm">
      <span className="flex items-center gap-2"><LoaderCircle size={17} className="animate-spin text-lime-600" />{label}</span>
    </div>
  );
}

function Empty({ label }: { label: string }) {
  return <p className="mt-5 rounded-xl border border-dashed border-slate-200 bg-slate-50 p-5 text-sm text-slate-500">{label}</p>;
}

function Login({ loggedIn }: { loggedIn: (context: Context) => void }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError("");
    try {
      await fetch(`${API}/panel/csrf/`, { credentials: "same-origin" });
      loggedIn(await api<Context>("/panel/login/", { method: "POST", body: JSON.stringify({ username, password }) }));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "No se ha podido iniciar sesión.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="grid min-h-screen place-items-center bg-[#070f1e] px-5">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_15%_15%,rgba(195,255,67,.16),transparent_27%),radial-gradient(circle_at_90%_90%,rgba(75,90,255,.24),transparent_30%)]" />
      <form onSubmit={submit} className="relative w-full max-w-md rounded-[28px] border border-white/10 bg-white/[.98] p-8 shadow-2xl">
        <div className="mb-8 flex items-center gap-3"><BrandMark size="h-12 w-12" /><div><h1 className="text-xl font-bold text-[#081120]">Relay</h1><p className="text-sm text-slate-500">Centro de control social</p></div></div>
        <p className="mb-6 text-sm leading-6 text-slate-600">Planifica, aprueba y publica desde un único espacio de trabajo.</p>
        <label className="mb-4 block text-sm font-semibold text-slate-700">Usuario<input autoComplete="username" required value={username} onChange={(event) => setUsername(event.target.value)} className="mt-1.5 w-full rounded-xl border border-slate-200 px-3 py-3 font-normal outline-none transition focus:border-lime-500 focus:ring-4 focus:ring-lime-100" /></label>
        <label className="block text-sm font-semibold text-slate-700">Contraseña<input type="password" autoComplete="current-password" required value={password} onChange={(event) => setPassword(event.target.value)} className="mt-1.5 w-full rounded-xl border border-slate-200 px-3 py-3 font-normal outline-none transition focus:border-lime-500 focus:ring-4 focus:ring-lime-100" /></label>
        {error && <p className="mt-4 rounded-xl bg-rose-50 p-3 text-sm text-rose-700">{error}</p>}
        <button disabled={loading} className="mt-6 flex w-full items-center justify-center gap-2 rounded-xl bg-[#0a1425] px-4 py-3 font-semibold text-[#ceff3f] transition hover:bg-[#101f37] disabled:opacity-60">{loading && <LoaderCircle size={17} className="animate-spin" />}Entrar en Relay</button>
      </form>
    </main>
  );
}

function Metric({ title, value, caption, danger }: { title: string; value: number; caption: string; danger?: boolean }) {
  return <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-[0_8px_22px_rgba(3,10,24,.035)]"><p className="text-sm font-medium text-slate-500">{title}</p><div className="mt-3 flex items-end justify-between gap-3"><p className={`text-3xl font-bold tracking-tight ${danger && value ? "text-rose-600" : "text-[#081120]"}`}>{value}</p><span className="rounded-md bg-slate-50 px-2 py-1 text-[10px] font-bold uppercase tracking-wide text-slate-500">{caption}</span></div></div>;
}

function Dashboard({ summary }: { summary: Summary | null }) {
  if (!summary) return <Loading />;
  const peak = Math.max(...summary.activity.map((item) => item.count), 1);
  return <>
    <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4"><Metric title="Publicadas" value={summary.published} caption="histórico" /><Metric title="En calendario" value={summary.scheduled} caption="pendientes" /><Metric title="Canales activos" value={summary.connections} caption="Meta" /><Metric title="Necesitan revisión" value={summary.failed} caption="errores" danger /></section>
    <section className="mt-5 grid gap-5 xl:grid-cols-[1.4fr_.8fr]">
      <div className="rounded-xl border border-[#173052] bg-[#091426] p-6 text-white shadow-[0_18px_45px_rgba(3,10,24,.16)]"><div className="flex items-start justify-between"><div><p className="text-xs font-bold uppercase tracking-[.14em] text-[#ceff3f]">Ritmo editorial</p><h2 className="mt-2 text-xl font-bold">Actividad de los últimos 7 días</h2></div><BarChart3 className="text-[#ceff3f]" size={21} /></div><div className="mt-10 flex h-44 items-end gap-3">{summary.activity.map((item) => <div key={item.date} className="flex h-full min-w-0 flex-1 flex-col justify-end gap-2"><div title={`${item.count} publicaciones`} className="min-h-1 rounded-t-md bg-gradient-to-t from-[#a6d33e] to-[#ceff3f] transition-all" style={{ height: `${Math.max(item.count ? (item.count / peak) * 100 : 3, 3)}%` }} /><p className="truncate text-center text-[10px] font-medium text-slate-400">{new Intl.DateTimeFormat("es-ES", { weekday: "narrow" }).format(new Date(`${item.date}T12:00:00`))}</p></div>)}</div></div>
      <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-[0_8px_22px_rgba(3,10,24,.035)]"><p className="text-xs font-bold uppercase tracking-[.12em] text-slate-500">Estado operativo</p><div className="mt-5 space-y-4"><div className="flex items-center justify-between"><span className="text-sm text-slate-600">Publicadas correctamente</span><span className="text-lg font-bold text-emerald-600">{summary.published}</span></div><div className="h-2 overflow-hidden rounded-full bg-slate-100"><div className="h-full rounded-full bg-emerald-500" style={{ width: `${summary.published + summary.scheduled + summary.failed ? (summary.published / (summary.published + summary.scheduled + summary.failed)) * 100 : 0}%` }} /></div><div className="flex items-center justify-between"><span className="text-sm text-slate-600">Programadas</span><span className="text-lg font-bold text-violet-600">{summary.scheduled}</span></div><div className="flex items-center justify-between"><span className="text-sm text-slate-600">Errores detectados</span><span className="text-lg font-bold text-rose-600">{summary.failed}</span></div></div></div>
    </section>
    <section className="mt-5 rounded-xl border border-slate-200 bg-white shadow-[0_8px_22px_rgba(3,10,24,.035)]"><div className="border-b border-slate-100 px-6 py-5"><h2 className="text-base font-bold text-[#081120]">Actividad reciente</h2><p className="mt-1 text-sm text-slate-500">Resultados recibidos desde Relay.</p></div>{summary.recent_publications.length === 0 ? <div className="px-6 pb-6"><Empty label="No hay publicaciones todavía." /></div> : <div className="divide-y divide-slate-100">{summary.recent_publications.map((item) => <div className="flex flex-wrap items-center gap-3 px-6 py-4" key={item.id}><div className="grid h-10 w-10 place-items-center rounded-lg bg-lime-50 text-lime-700">{item.channel.includes("INSTAGRAM") ? <Instagram size={19} /> : <Send size={18} />}</div><div className="min-w-52 flex-1"><p className="font-semibold text-slate-800">{item.title}</p><p className="mt-1 text-xs text-slate-500">{item.account} · {formatDate(item.scheduled_for)}</p></div><State value={item.state} /></div>)}</div>}</section>
  </>;
}

function Connections({ brand, connections, refresh }: { brand: Brand; connections: Connection[]; refresh: () => Promise<void> }) {
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  async function startMeta() { setBusy(true); setError(""); try { const result = await api<{ authorization_url: string }>("/oauth/meta/start/", { method: "POST", body: JSON.stringify({ brand_id: brand.id }) }); window.location.assign(result.authorization_url); } catch (reason) { setError(reason instanceof Error ? reason.message : "No se ha podido conectar Meta."); setBusy(false); } }
  return <section className="rounded-xl border border-slate-200 bg-white shadow-[0_8px_22px_rgba(3,10,24,.035)]"><div className="flex flex-wrap items-start justify-between gap-4 border-b border-slate-100 p-6"><div><h2 className="text-xl font-bold text-[#081120]">Conexiones</h2><p className="mt-1 text-sm text-slate-500">Canales autorizados para {brand.name}.</p></div><button onClick={() => void startMeta()} disabled={busy} className="flex items-center gap-2 rounded-lg bg-[#0a1425] px-4 py-2.5 text-sm font-semibold text-[#ceff3f] disabled:opacity-60"><Link2 size={17} />{busy ? "Abriendo Meta…" : "Conectar Meta"}</button></div>{error && <p className="mx-6 mt-5 rounded-xl bg-rose-50 p-3 text-sm text-rose-700">{error}</p>}<div className="grid gap-3 p-6 md:grid-cols-2">{connections.length === 0 ? <Empty label="Aún no hay conexiones para esta marca." /> : connections.map((connection) => <div className="rounded-xl border border-slate-200 p-5" key={connection.id}><div className="flex items-center justify-between"><div className="grid h-11 w-11 place-items-center rounded-lg bg-slate-50 text-[#0a1425]">{connection.channel.includes("INSTAGRAM") ? <Instagram size={21} /> : <Send size={20} />}</div><span className={`flex items-center gap-1.5 text-[10px] font-bold tracking-wide ${connection.is_active ? "text-emerald-600" : "text-slate-400"}`}><span className={`h-2 w-2 rounded-full ${connection.is_active ? "bg-emerald-500" : "bg-slate-300"}`} />{connection.is_active ? "ACTIVA" : "INACTIVA"}</span></div><h3 className="mt-5 font-bold text-slate-800">{connection.display_name}</h3><p className="mt-1 text-sm text-slate-500">{channelName(connection.channel)} · Meta</p></div>)}</div><button onClick={() => void refresh()} className="mx-6 mb-6 text-sm font-semibold text-lime-700">Actualizar datos</button></section>;
}

function Content({ posts, create }: { posts: Post[]; create: () => void }) {
  return <section className="rounded-xl border border-slate-200 bg-white shadow-[0_8px_22px_rgba(3,10,24,.035)]"><div className="flex flex-wrap items-start justify-between gap-4 border-b border-slate-100 p-6"><div><h2 className="text-xl font-bold text-[#081120]">Contenido</h2><p className="mt-1 text-sm text-slate-500">Borradores, aprobaciones y contenido listo para publicar.</p></div><button onClick={create} className="flex items-center gap-2 rounded-lg bg-[#0a1425] px-4 py-2.5 text-sm font-semibold text-[#ceff3f]"><Plus size={17} />Crear publicación</button></div>{posts.length === 0 ? <div className="p-6"><Empty label="Aún no hay contenido para esta marca." /></div> : <div className="divide-y divide-slate-100">{posts.map((post) => <article key={post.id} className="flex flex-wrap items-center gap-3 px-6 py-4"><div className="grid h-10 w-10 place-items-center rounded-lg bg-indigo-50 text-indigo-600"><FileText size={19} /></div><div className="min-w-56 flex-1"><h3 className="font-semibold text-slate-800">{post.title || post.body.slice(0, 80)}</h3><p className="mt-1 line-clamp-1 text-sm text-slate-500">{post.body}</p></div><State value={post.state} /></article>)}</div>}</section>;
}

function Calendar({ publications, connections }: { publications: Publication[]; connections: Connection[] }) {
  const [mode, setMode] = useState<"month" | "table">("month");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const accounts = useMemo(() => new Map(connections.map((item) => [item.id, item.display_name])), [connections]);
  const events = useMemo<EventInput[]>(() => publications.map((item) => ({ id: item.id, title: accounts.get(item.channel_connection_id) ?? "Canal conectado", start: item.scheduled_for, classNames: [`relay-event-${item.state.toLowerCase()}`] })), [accounts, publications]);
  const ordered = useMemo(() => [...publications].sort((first, second) => new Date(first.scheduled_for).getTime() - new Date(second.scheduled_for).getTime()), [publications]);
  const selected = publications.find((item) => item.id === selectedId);

  return <section className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-[0_8px_22px_rgba(3,10,24,.035)]"><div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-100 p-6"><div><h2 className="text-xl font-bold text-[#081120]">Calendario editorial</h2><p className="mt-1 text-sm text-slate-500">Planifica la distribución y supervisa cada publicación.</p></div><div className="flex rounded-lg border border-slate-200 bg-slate-50 p-1"><button onClick={() => setMode("month")} className={`flex items-center gap-2 rounded-md px-3 py-2 text-sm font-semibold ${mode === "month" ? "bg-white text-[#081120] shadow-sm" : "text-slate-500"}`}><Grid2X2 size={16} />Calendario</button><button onClick={() => setMode("table")} className={`flex items-center gap-2 rounded-md px-3 py-2 text-sm font-semibold ${mode === "table" ? "bg-white text-[#081120] shadow-sm" : "text-slate-500"}`}><List size={16} />Tabla</button></div></div>
    {publications.length === 0 ? <div className="p-6"><Empty label="No hay publicaciones en calendario." /></div> : mode === "month" ? <div className="grid xl:grid-cols-[minmax(0,1fr)_260px]"><div className="relay-calendar p-4 sm:p-6"><FullCalendar plugins={[dayGridPlugin, timeGridPlugin, interactionPlugin]} locale={esLocale} initialView="dayGridMonth" firstDay={1} height="auto" allDaySlot={false} slotMinTime="06:00:00" slotMaxTime="23:00:00" headerToolbar={{ left: "prev,next today", center: "title", right: "dayGridMonth,timeGridWeek,timeGridDay" }} buttonText={{ today: "Hoy", month: "Mes", week: "Semana", day: "Día" }} events={events} eventClick={(info) => setSelectedId(info.event.id)} /></div><aside className="border-t border-slate-100 bg-slate-50/70 p-5 xl:border-l xl:border-t-0"><p className="text-[10px] font-bold uppercase tracking-[.12em] text-slate-500">Detalle de publicación</p>{selected ? <div className="mt-4"><p className="font-semibold text-slate-800">{accounts.get(selected.channel_connection_id) ?? "Canal conectado"}</p><p className="mt-2 text-sm text-slate-500">{formatDate(selected.scheduled_for)}</p><div className="mt-4"><State value={selected.state} /></div>{selected.last_error_message && <p className="mt-4 rounded-lg bg-rose-50 p-3 text-xs text-rose-700">{selected.last_error_message}</p>}</div> : <p className="mt-4 text-sm leading-6 text-slate-500">Selecciona una publicación en el calendario para ver su estado.</p>}</aside></div> : <div className="overflow-x-auto"><table className="w-full min-w-[680px] text-left"><thead className="bg-slate-50 text-[10px] font-bold uppercase tracking-[.1em] text-slate-500"><tr><th className="px-6 py-3">Fecha</th><th className="px-6 py-3">Canal</th><th className="px-6 py-3">Hora</th><th className="px-6 py-3">Estado</th><th className="px-6 py-3">Incidencia</th></tr></thead><tbody className="divide-y divide-slate-100">{ordered.map((item) => <tr key={item.id} className="transition hover:bg-slate-50"><td className="px-6 py-4 text-sm font-semibold text-slate-800">{formatDay(item.scheduled_for)}</td><td className="px-6 py-4 text-sm text-slate-600">{accounts.get(item.channel_connection_id) ?? "Canal conectado"}</td><td className="px-6 py-4 text-sm text-slate-600">{new Intl.DateTimeFormat("es-ES", { hour: "2-digit", minute: "2-digit" }).format(new Date(item.scheduled_for))}</td><td className="px-6 py-4"><State value={item.state} /></td><td className="max-w-xs px-6 py-4 text-sm text-rose-600">{item.last_error_message || "—"}</td></tr>)}</tbody></table></div>}</section>;
}

function Composer({ brand, connections, close, saved }: { brand: Brand; connections: Connection[]; close: () => void; saved: () => Promise<void> }) {
  const [title, setTitle] = useState(""); const [body, setBody] = useState(""); const [image, setImage] = useState<File | null>(null); const [when, setWhen] = useState(""); const [targets, setTargets] = useState<string[]>([]); const [error, setError] = useState(""); const [busy, setBusy] = useState(false);
  async function mediaAsset() { if (!image) throw new Error("Selecciona una imagen JPG o PNG."); if (!["image/jpeg", "image/png"].includes(image.type)) throw new Error("Solo se admiten imágenes JPG o PNG."); const bytes = await image.arrayBuffer(); const digest = await crypto.subtle.digest("SHA-256", bytes); const checksum = Array.from(new Uint8Array(digest)).map((byte) => byte.toString(16).padStart(2, "0")).join(""); const intent = await api<{ asset: { id: string }; upload_url: string; upload_headers: Record<string, string> }>("/media/upload-intents/", { method: "POST", body: JSON.stringify({ brand_id: brand.id, filename: image.name, content_type: image.type, size_bytes: image.size, checksum }) }); const upload = await fetch(intent.upload_url, { method: "PUT", headers: intent.upload_headers, body: image }); if (!upload.ok) throw new Error("El bucket ha rechazado la imagen. Hay que revisar CORS en B2."); await api(`/media/${intent.asset.id}/confirm/`, { method: "POST" }); return intent.asset.id; }
  async function save(schedule: boolean) { setError(""); setBusy(true); try { if (schedule && (!when || !targets.length)) throw new Error("Elige una fecha, hora y al menos una cuenta."); const assetId = await mediaAsset(); const post = await api<Post>("/posts/", { method: "POST", headers: { "Idempotency-Key": crypto.randomUUID() }, body: JSON.stringify({ brand_id: brand.id, title, body, media_asset_ids: [assetId] }) }); if (schedule) { await api(`/posts/${post.id}/approve/`, { method: "POST" }); await Promise.all(targets.map((connectionId) => api("/publications/", { method: "POST", headers: { "Idempotency-Key": crypto.randomUUID() }, body: JSON.stringify({ post_variant_id: post.default_variant_id, channel_connection_id: connectionId, scheduled_for: new Date(when).toISOString() }) }))); } await saved(); close(); } catch (reason) { setError(reason instanceof Error ? reason.message : "No se ha podido guardar la publicación."); } finally { setBusy(false); } }
  return <div className="fixed inset-0 z-50 overflow-y-auto bg-[#07101fcc] p-4 backdrop-blur-sm"><div className="mx-auto my-6 max-w-2xl rounded-[24px] bg-white p-6 shadow-2xl"><div className="flex items-start justify-between gap-5"><div><p className="text-sm font-semibold text-lime-700">{brand.name}</p><h2 className="mt-1 text-2xl font-bold text-[#081120]">Nueva publicación</h2></div><button onClick={close} className="rounded-xl px-3 py-2 text-sm font-semibold text-slate-500 hover:bg-slate-100">Cerrar</button></div><label className="mt-6 block text-sm font-semibold text-slate-700">Título<input value={title} onChange={(event) => setTitle(event.target.value)} className="mt-1.5 w-full rounded-xl border border-slate-200 px-3 py-2.5 font-normal outline-none focus:border-lime-500" /></label><label className="mt-4 block text-sm font-semibold text-slate-700">Texto<textarea required rows={7} value={body} onChange={(event) => setBody(event.target.value)} className="mt-1.5 w-full resize-y rounded-xl border border-slate-200 px-3 py-2.5 font-normal outline-none focus:border-lime-500" /></label><label className="mt-4 block rounded-xl border border-dashed border-slate-300 p-4 text-sm font-semibold text-slate-700"><span className="flex items-center gap-2"><ImagePlus size={18} className="text-lime-700" />{image?.name ?? "Imagen JPG o PNG"}</span><input required type="file" accept="image/jpeg,image/png" onChange={(event) => setImage(event.target.files?.[0] ?? null)} className="mt-3 block w-full font-normal" /></label><div className="mt-5 rounded-xl bg-slate-50 p-4"><p className="text-sm font-bold text-slate-700">Programar ahora</p><input type="datetime-local" value={when} onChange={(event) => setWhen(event.target.value)} className="mt-3 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm" /><div className="mt-3 grid gap-2 sm:grid-cols-2">{connections.map((connection) => <label className="flex items-center gap-2 rounded-lg bg-white p-2 text-sm text-slate-700" key={connection.id}><input type="checkbox" checked={targets.includes(connection.id)} onChange={() => setTargets((items) => items.includes(connection.id) ? items.filter((id) => id !== connection.id) : [...items, connection.id])} />{channelName(connection.channel)} · {connection.display_name}</label>)}</div></div>{error && <p className="mt-4 rounded-xl bg-rose-50 p-3 text-sm text-rose-700">{error}</p>}<div className="mt-6 flex flex-wrap justify-end gap-3"><button disabled={busy} onClick={() => void save(false)} className="rounded-lg border border-slate-200 px-4 py-2.5 text-sm font-semibold text-slate-700 disabled:opacity-50">Guardar borrador</button><button disabled={busy} onClick={() => void save(true)} className="flex items-center gap-2 rounded-lg bg-[#0a1425] px-4 py-2.5 text-sm font-semibold text-[#ceff3f] disabled:opacity-50">{busy && <LoaderCircle size={16} className="animate-spin" />}Aprobar y programar</button></div></div></div>;
}

function Panel({ context, logout }: { context: Context; logout: () => Promise<void> }) {
  const [page, setPage] = useState<Page>("dashboard"); const [brandId, setBrandId] = useState(context.selected_brand_id ?? context.brands[0]?.id ?? ""); const [summary, setSummary] = useState<Summary | null>(null); const [connections, setConnections] = useState<Connection[]>([]); const [posts, setPosts] = useState<Post[]>([]); const [publications, setPublications] = useState<Publication[]>([]); const [composer, setComposer] = useState(false); const [error, setError] = useState("");
  const brand = useMemo(() => context.brands.find((item) => item.id === brandId) ?? context.brands[0], [brandId, context.brands]);
  async function refresh() { if (!brand) return; setError(""); try { const [nextSummary, nextConnections, nextPosts, nextPublications] = await Promise.all([api<Summary>("/panel/summary/"), api<Connection[]>(`/connections/?brand_id=${brand.id}`), api<Post[]>(`/posts/?brand_id=${brand.id}`), api<Publication[]>(`/publications/?brand_id=${brand.id}`)]); setSummary(nextSummary); setConnections(nextConnections); setPosts(nextPosts); setPublications(nextPublications); } catch (reason) { setError(reason instanceof Error ? reason.message : "No se han podido cargar los datos."); } }
  useEffect(() => { void refresh(); }, [brandId]);
  if (!brand) return <Loading label="Tu usuario aún no tiene una marca activa." />;
  const nav: Array<{ id: Page; label: string; icon: typeof LayoutDashboard }> = [{ id: "dashboard", label: "Resumen", icon: LayoutDashboard }, { id: "calendar", label: "Calendario", icon: CalendarDays }, { id: "content", label: "Contenido", icon: FileText }, { id: "connections", label: "Conexiones", icon: Link2 }, { id: "settings", label: "Ajustes", icon: Settings }];
  const screen = page === "dashboard" ? <Dashboard summary={summary} /> : page === "calendar" ? <Calendar publications={publications} connections={connections} /> : page === "content" ? <Content posts={posts} create={() => setComposer(true)} /> : page === "connections" ? <Connections brand={brand} connections={connections} refresh={refresh} /> : <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm"><h2 className="text-xl font-bold">Ajustes</h2><p className="mt-2 text-sm text-slate-500">La gestión de equipo y marca se activará en el siguiente bloque.</p></section>;
  const pageTitle = page === "dashboard" ? "Resumen operativo" : nav.find((item) => item.id === page)?.label;
  return <div className="min-h-screen bg-[#eef1f6]"><aside className="fixed inset-y-0 left-0 hidden w-72 border-r border-white/5 bg-[#081120] text-white lg:block"><div className="flex h-20 items-center gap-3 border-b border-white/10 px-5"><BrandMark /><div><p className="font-bold tracking-tight">Relay</p><p className="text-[10px] font-semibold uppercase tracking-[.12em] text-slate-400">Control social</p></div></div><div className="p-4"><p className="mb-3 px-3 text-[10px] font-bold uppercase tracking-[.14em] text-slate-500">Espacio de trabajo</p><nav className="space-y-1">{nav.map((item) => { const Icon = item.icon; return <button onClick={() => setPage(item.id)} key={item.id} className={`flex w-full items-center gap-3 rounded-lg px-3 py-3 text-sm font-medium transition ${page === item.id ? "bg-[#ceff3f] text-[#07101f] shadow-[0_5px_15px_rgba(206,255,63,.14)]" : "text-slate-400 hover:bg-white/8 hover:text-white"}`}><Icon size={18} />{item.label}{page === item.id && <ChevronRight className="ml-auto" size={15} />}</button>; })}</nav></div><div className="absolute inset-x-4 bottom-4 rounded-xl border border-white/10 bg-white/[.045] p-4"><p className="text-[10px] font-bold uppercase tracking-[.12em] text-[#ceff3f]">{context.workspace.name}</p><div className="mt-3 flex items-center gap-2"><span className="grid h-8 w-8 place-items-center rounded-lg bg-white/10 text-xs font-bold">{initials(context.user.display_name)}</span><p className="truncate text-sm font-semibold">{context.user.display_name}</p></div><button onClick={() => void logout()} className="mt-4 flex items-center gap-2 text-xs font-semibold text-slate-400 hover:text-white"><LogOut size={14} />Cerrar sesión</button></div></aside><main className="lg:ml-72"><header className="flex min-h-20 items-center justify-between gap-4 border-b border-slate-200 bg-white px-5 lg:px-8"><div className="flex items-center gap-3"><BrandMark size="h-9 w-9 lg:hidden" /><div className="hidden items-center rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-400 xl:flex"><Search size={16} /><span className="ml-2 min-w-56">Buscar contenido…</span><kbd className="ml-5 rounded border border-slate-200 bg-white px-1.5 py-0.5 text-[10px]">⌘ K</kbd></div></div><div className="flex items-center gap-3"><button className="grid h-9 w-9 place-items-center rounded-lg border border-slate-200 text-slate-500 hover:bg-slate-50" aria-label="Notificaciones"><Bell size={17} /></button><div className="relative"><select value={brand.id} onChange={(event) => setBrandId(event.target.value)} className="appearance-none rounded-lg border border-slate-200 bg-white py-2 pl-3 pr-9 text-sm font-semibold text-slate-700 outline-none">{context.brands.map((item) => <option value={item.id} key={item.id}>{item.name}</option>)}</select><ChevronDown className="pointer-events-none absolute right-2 top-2.5 text-slate-500" size={15} /></div><button onClick={() => setComposer(true)} className="flex items-center gap-2 rounded-lg bg-[#0a1425] px-4 py-2.5 text-sm font-semibold text-[#ceff3f] shadow-lg shadow-slate-200"><Plus size={17} />Nueva publicación</button></div></header><div className="mx-auto max-w-[1500px] p-5 lg:p-8"><div className="mb-7 flex items-end justify-between"><div><div className="flex items-center gap-2 text-xs font-medium text-slate-500"><span>{context.workspace.name}</span><ChevronRight size={13} /><span>{brand.name}</span></div><h1 className="mt-2 text-3xl font-bold tracking-tight text-[#081120]">{pageTitle}</h1><p className="mt-1.5 text-sm text-slate-500">Datos operativos del espacio de trabajo actual.</p></div><div className="hidden items-center gap-2 rounded-lg border border-lime-200 bg-lime-50 px-3 py-2 text-xs font-semibold text-lime-800 md:flex"><Sparkles size={15} />Relay está listo para publicar</div></div>{error && <div className="mb-6 flex items-center gap-2 rounded-xl bg-rose-50 p-4 text-sm text-rose-700"><CircleAlert size={18} />{error}</div>}{screen}</div></main>{composer && <Composer brand={brand} connections={connections} close={() => setComposer(false)} saved={refresh} />}</div>;
}

function ContextSwitcher({ context }: { context: Context }) {
  const selectedValue = `${context.workspace.id}:${context.selected_brand_id ?? ""}`;
  return (
    <label className="context-switcher">
      <span>Marca</span>
      <select
        value={selectedValue}
        onChange={(event) => {
          const [workspaceId, brandId] = event.target.value.split(":");
          window.location.assign(
            `/api/v1/panel/workspace/?workspace_id=${encodeURIComponent(workspaceId)}&brand_id=${encodeURIComponent(brandId)}`,
          );
        }}
      >
        {context.workspaces.map((workspace) => <optgroup key={workspace.id} label={workspace.name}>
          {workspace.brands.map((brand) => (
            <option key={brand.id} value={`${workspace.id}:${brand.id}`}>
              {workspace.name} · {brand.name}
            </option>
          ))}
        </optgroup>)}
      </select>
    </label>
  );
}

export function App() {
  const [context, setContext] = useState<Context | null>(null);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    api("/panel/csrf/")
      .then(() => api<Context>("/panel/me/"))
      .then(setContext)
      .catch(() => undefined)
      .finally(() => setLoading(false));
  }, []);
  if (loading) return <Loading label="Abriendo Relay…" />;
  if (!context) return <Login loggedIn={setContext} />;
  return <>
    <ContextSwitcher context={context} />
    <Panel key={context.workspace.id} context={context} logout={async () => { await api("/panel/logout/", { method: "POST" }); setContext(null); }} />
  </>;
}
