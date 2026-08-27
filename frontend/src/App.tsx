import type { LucideIcon } from "lucide-react";
import {
  ArrowUpRight,
  CalendarDays,
  CheckCircle2,
  ChevronDown,
  Clock3,
  FileText,
  Instagram,
  LayoutDashboard,
  Link2,
  MoreHorizontal,
  Plus,
  Send,
  Settings,
  Users,
} from "lucide-react";

type NavigationItem = { label: string; icon: LucideIcon; active?: boolean };

const navigation: NavigationItem[] = [
  { label: "Resumen", icon: LayoutDashboard, active: true },
  { label: "Calendario", icon: CalendarDays },
  { label: "Contenido", icon: FileText },
  { label: "Aprobaciones", icon: CheckCircle2 },
  { label: "Analítica", icon: ArrowUpRight },
];

const scheduledPosts = [
  { day: "LUN", date: "18", title: "Casas de verano, mejores resultados", channel: "Facebook", tone: "bg-blue-500" },
  { day: "MIÉ", date: "20", title: "Una nueva forma de entrenar", channel: "Instagram", tone: "bg-fuchsia-500" },
  { day: "VIE", date: "22", title: "Tu próxima visita empieza aquí", channel: "Instagram", tone: "bg-orange-500" },
];

const activity = [
  { title: "Campaña aprobada", detail: "North Studio · hace 12 min", icon: CheckCircle2, tone: "bg-emerald-100 text-emerald-700" },
  { title: "Cuenta de Instagram conectada", detail: "Fit Collective · hace 1 h", icon: Instagram, tone: "bg-pink-100 text-pink-700" },
  { title: "Publicación lista para revisar", detail: "Coastal Living · hace 3 h", icon: FileText, tone: "bg-violet-100 text-violet-700" },
];

function NavItem({ item }: { item: NavigationItem }) {
  const Icon = item.icon;
  return (
    <button className={`flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition ${item.active ? "bg-white text-brand shadow-sm" : "text-slate-500 hover:bg-white/70 hover:text-slate-900"}`}>
      <Icon size={18} strokeWidth={2.1} />
      {item.label}
    </button>
  );
}

function Metric({ label, value, change, positive = true }: { label: string; value: string; change: string; positive?: boolean }) {
  return (
    <div className="rounded-2xl border border-slate-100 bg-white p-5 shadow-[0_12px_32px_rgba(31,38,72,0.04)]">
      <p className="text-sm font-medium text-slate-500">{label}</p>
      <div className="mt-3 flex items-end justify-between gap-3"><p className="text-3xl font-semibold tracking-tight text-ink">{value}</p><span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${positive ? "bg-emerald-50 text-emerald-700" : "bg-rose-50 text-rose-700"}`}>{change}</span></div>
    </div>
  );
}

export function App() {
  return (
    <div className="min-h-screen bg-[#f7f8fc]">
      <aside className="fixed inset-y-0 left-0 hidden w-64 border-r border-slate-200/70 bg-[#f1f3fb] p-5 lg:block">
        <div className="mb-10 flex items-center gap-3 px-2"><div className="grid h-9 w-9 place-items-center rounded-xl bg-brand font-black text-white">R</div><span className="text-lg font-bold tracking-tight">Relay</span></div>
        <div className="space-y-1">{navigation.map((item) => <NavItem key={item.label} item={item} />)}</div>
        <div className="mt-10"><p className="mb-3 px-3 text-[11px] font-bold uppercase tracking-[0.16em] text-slate-400">Espacio de trabajo</p><button className="flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium text-slate-500 hover:bg-white"><Users size={18} /> Equipo y roles</button><button className="flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium text-slate-500 hover:bg-white"><Link2 size={18} /> Conexiones</button><button className="flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium text-slate-500 hover:bg-white"><Settings size={18} /> Ajustes</button></div>
        <div className="absolute inset-x-5 bottom-5 rounded-2xl bg-ink p-4 text-white"><p className="text-xs font-semibold text-slate-300">Relay para agencias</p><p className="mt-1 text-sm font-semibold">Haz que cada publicación cuente.</p></div>
      </aside>
      <main className="lg:ml-64">
        <header className="flex h-20 items-center justify-between border-b border-slate-200/70 bg-white/75 px-6 backdrop-blur lg:px-10"><div className="lg:hidden flex items-center gap-2 font-bold"><div className="grid h-8 w-8 place-items-center rounded-lg bg-brand text-white">R</div>Relay</div><div className="hidden items-center gap-2 text-sm text-slate-500 lg:flex"><span>Espacio de trabajo</span><button className="flex items-center gap-2 rounded-lg bg-slate-100 px-3 py-2 font-semibold text-slate-700">Aleya Cloud <ChevronDown size={15} /></button></div><div className="flex items-center gap-3"><button className="hidden rounded-xl border border-slate-200 px-3 py-2 text-sm font-medium text-slate-600 sm:block">18 – 24 ago.</button><button className="flex items-center gap-2 rounded-xl bg-brand px-4 py-2.5 text-sm font-semibold text-white shadow-lg shadow-indigo-200"><Plus size={17} /> Nueva publicación</button><div className="grid h-9 w-9 place-items-center rounded-full bg-amber-100 text-sm font-bold text-amber-800">JG</div></div></header>
        <div className="mx-auto max-w-7xl p-6 lg:p-10"><div className="flex flex-wrap items-end justify-between gap-4"><div><p className="text-sm font-semibold text-brand">Buenos días, Jorge</p><h1 className="mt-1 text-3xl font-bold tracking-tight text-ink">Haz visible esta semana.</h1><p className="mt-2 text-slate-500">Tu contenido, aprobaciones y resultados, en un mismo lugar.</p></div><button className="flex items-center gap-2 text-sm font-semibold text-slate-600">Ver informe <ArrowUpRight size={17} /></button></div>
          <section className="mt-8 grid gap-4 sm:grid-cols-2 xl:grid-cols-4"><Metric label="Publicadas este mes" value="24" change="+18%" /><Metric label="Alcance total" value="48.2K" change="+12,4%" /><Metric label="Interacción" value="6,8%" change="+1,9%" /><Metric label="Pendientes de aprobación" value="3" change="Requiere atención" positive={false} /></section>
          <section className="mt-8 grid gap-6 xl:grid-cols-[1.45fr_0.85fr]"><div className="rounded-2xl border border-slate-100 bg-white p-6 shadow-[0_12px_32px_rgba(31,38,72,0.04)]"><div className="flex items-center justify-between"><div><h2 className="text-lg font-bold">Calendario editorial</h2><p className="mt-1 text-sm text-slate-500">Esta semana en tus marcas</p></div><button className="rounded-lg p-2 text-slate-400 hover:bg-slate-50"><MoreHorizontal size={20} /></button></div><div className="mt-6 space-y-3">{scheduledPosts.map((post) => <div key={post.date} className="flex items-center gap-4 rounded-xl border border-slate-100 p-3.5 transition hover:border-indigo-100 hover:bg-indigo-50/30"><div className="w-10 text-center"><p className="text-[10px] font-bold tracking-wider text-slate-400">{post.day}</p><p className="text-xl font-bold">{post.date}</p></div><span className={`h-10 w-1 rounded-full ${post.tone}`} /><div className="min-w-0 flex-1"><p className="truncate font-semibold text-slate-800">{post.title}</p><p className="mt-1 text-xs text-slate-500">Aleya Cloud · {post.channel}</p></div><Clock3 size={17} className="text-slate-400" /></div>)}</div></div>
            <div className="rounded-2xl border border-slate-100 bg-white p-6 shadow-[0_12px_32px_rgba(31,38,72,0.04)]"><div className="flex items-center justify-between"><div><h2 className="text-lg font-bold">Actividad reciente</h2><p className="mt-1 text-sm text-slate-500">Lo que ha cambiado en Relay</p></div><Send size={18} className="text-brand" /></div><div className="mt-5 space-y-5">{activity.map((item) => { const Icon = item.icon; return <div key={item.title} className="flex gap-3"><div className={`grid h-9 w-9 shrink-0 place-items-center rounded-xl ${item.tone}`}><Icon size={17} /></div><div><p className="text-sm font-semibold text-slate-800">{item.title}</p><p className="mt-1 text-xs text-slate-500">{item.detail}</p></div></div>; })}</div><button className="mt-6 w-full rounded-xl bg-slate-50 px-4 py-2.5 text-sm font-semibold text-slate-600 hover:bg-slate-100">Abrir registro de actividad</button></div></section>
        </div>
      </main>
    </div>
  );
}
