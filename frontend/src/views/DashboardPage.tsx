import React, { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api/http'

interface RoomItem {
  id: string
  code: string
  title: string | null
  name?: string | null
  max_participants: number
  status: string
  created_at: string
}

interface CreateRoomForm {
  title: string
  max_participants: number
}

export const DashboardPage: React.FC = () => {
  const navigate = useNavigate()

  const [rooms, setRooms] = useState<RoomItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [form, setForm] = useState<CreateRoomForm>({
    title: '',
    max_participants: 20,
  })
  const [creating, setCreating] = useState(false)

  const normalizeRoom = (raw: any): RoomItem => {
    return {
      id: String(raw.id),
      code: String(raw.code),
      title: raw.title ?? raw.name ?? null,
      name: raw.name ?? raw.title ?? null,
      max_participants: Number(raw.max_participants ?? 20),
      status: String(raw.status ?? 'active'),
      created_at: String(raw.created_at ?? new Date().toISOString()),
    }
  }

  const loadRooms = async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await api.get<any>('/rooms/my')

      const raw = res.data
      let listRaw: any[] = []

      if (Array.isArray(raw)) {
        listRaw = raw
      } else if (raw && Array.isArray(raw.rooms)) {
        listRaw = raw.rooms
      } else {
        listRaw = []
      }

      const list = listRaw.map(normalizeRoom)
      setRooms(list)
    } catch (e: any) {
      console.error(e)
      setError(e?.response?.data?.detail || 'Не удалось загрузить список комнат')
      setRooms([])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadRooms()
  }, [])

  const handleChange = (field: keyof CreateRoomForm, value: string | number) => {
    setForm((prev) => ({
      ...prev,
      [field]: value,
    }))
  }

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault()
    setCreating(true)
    setError(null)
    try {
      const title = form.title.trim() || null
      const payload = {
        title,
        name: title, // <-- и title, и name, чтобы бэкенд точно получил название
        max_participants: form.max_participants,
      }
      const res = await api.post<any>('/rooms/', payload)
      const room = normalizeRoom(res.data)
      setRooms((prev) => [room, ...prev])
      setForm({
        title: '',
        max_participants: 20,
      })
    } catch (e: any) {
      console.error(e)
      setError(e?.response?.data?.detail || 'Не удалось создать комнату')
    } finally {
      setCreating(false)
    }
  }

  const handleOpenRoom = (room: RoomItem) => {
    navigate(`/rooms/${room.code}`)
  }

  const buildInviteLink = (room: RoomItem): string => {
    const origin = window.location.origin
    return `${origin}/g/${room.code}`
  }

  const copyInviteLink = async (room: RoomItem) => {
    const link = buildInviteLink(room)
    try {
      await navigator.clipboard.writeText(link)
      alert('Ссылка приглашения скопирована в буфер обмена:\n' + link)
    } catch (e) {
      console.error(e)
      setError(
        'Не удалось скопировать ссылку автоматически. Можно выделить и скопировать её из поля вручную.',
      )
    }
  }

  const formatDateTime = (iso: string) => {
    const d = new Date(iso)
    if (isNaN(d.getTime())) return iso
    return d.toLocaleString()
  }

  return (
    <div className="space-y-6">
      {/* Верхний блок с описанием */}
      <section className="bg-slate-900 border border-slate-800 rounded-2xl p-4">
        <h1 className="text-xl font-semibold mb-2">Мои комнаты</h1>
        <p className="text-sm text-slate-400 max-w-2xl">
          Здесь ты создаёшь тихие комнаты для курсов, консультаций и встреч.
          У каждой комнаты есть свой код и ссылка приглашения — просто скопируй её
          и отправь участникам в мессенджер или по email.
        </p>
      </section>

      {/* Форма создания комнаты */}
      <section className="bg-slate-900 border border-slate-800 rounded-2xl p-4">
        <h2 className="text-lg font-semibold mb-3">Создать новую комнату</h2>
        <form onSubmit={handleCreate} className="space-y-3">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div>
              <label className="block text-xs text-slate-400 mb-1">
                Название комнаты
              </label>
              <input
                className="w-full rounded-lg bg-slate-950 border border-slate-700 px-3 py-2 text-sm focus:outline-none focus:border-sky-500"
                placeholder="Например: Семинар по телесной терапии"
                value={form.title}
                onChange={(e) => handleChange('title', e.target.value)}
              />
            </div>
            <div>
              <label className="block text-xs text-slate-400 mb-1">
                Максимум участников
              </label>
              <input
                type="number"
                min={2}
                max={50}
                className="w-full rounded-lg bg-slate-950 border border-slate-700 px-3 py-2 text-sm focus:outline-none focus:border-sky-500"
                value={form.max_participants}
                onChange={(e) =>
                  handleChange('max_participants', Number(e.target.value) || 2)
                }
              />
              <p className="text-[11px] text-slate-500 mt-1">
                Для текущего тарифа оптимально 10–20 человек в одной комнате.
              </p>
            </div>
          </div>
          {error && <div className="text-xs text-red-400">{error}</div>}
          <div className="flex items-center gap-3 pt-1">
            <button
              type="submit"
              disabled={creating}
              className="px-4 py-2 rounded-lg bg-sky-600 hover:bg-sky-500 text-sm font-medium disabled:opacity-60"
            >
              {creating ? 'Создаём...' : 'Создать комнату'}
            </button>
          </div>
        </form>
      </section>

      {/* Список комнат */}
      <section className="bg-slate-900 border border-slate-800 rounded-2xl p-4">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-lg font-semibold">Активные комнаты</h2>
          {loading && <span className="text-xs text-slate-500">Обновляем...</span>}
        </div>

        {rooms.length === 0 && !loading ? (
          <div className="text-sm text-slate-500">
            Пока нет ни одной комнаты. Создай первую — и сразу получишь ссылку, которую можно
            отправить участникам.
          </div>
        ) : (
          <div className="space-y-2">
            {rooms.map((room) => {
              const statusLabel =
                room.status === 'active'
                  ? 'Активна'
                  : room.status === 'scheduled'
                  ? 'Запланирована'
                  : 'Черновик'

              const inviteLink = buildInviteLink(room)

              return (
                <div
                  key={room.id}
                  className="bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-sm"
                >
                  <div className="flex flex-col gap-2">
                    <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
                      <div>
                        <div className="font-medium text-slate-100">
                          {room.title || 'Без названия'}
                        </div>
                        <div className="text-xs text-slate-400">
                          Код комнаты:{' '}
                          <span className="font-mono text-slate-200">{room.code}</span>
                        </div>
                        <div className="text-[11px] text-slate-500">
                          Создана: {formatDateTime(room.created_at)} · участников до{' '}
                          {room.max_participants}
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <span
                          className={
                            'px-2 py-0.5 rounded-full text-[11px] border ' +
                            (room.status === 'active'
                              ? 'border-emerald-400 text-emerald-300'
                              : 'border-slate-700 text-slate-500')
                          }
                        >
                          {statusLabel}
                        </span>
                        <button
                          onClick={() => handleOpenRoom(room)}
                          className="px-3 py-1 rounded-full bg-sky-600 hover:bg-sky-500 text-white text-xs"
                        >
                          Войти в комнату
                        </button>
                      </div>
                    </div>

                    {/* Блок ссылок и приглашений */}
                    <div className="mt-1 border-t border-slate-800 pt-2">
                      <div className="text-[11px] text-slate-400 mb-1">
                        Ссылка для приглашения участников (гостевой вход без регистрации):
                      </div>
                      <div className="flex flex-col sm:flex-row sm:items-center gap-2">
                        <div className="flex-1">
                          <input
                            className="w-full rounded-lg bg-slate-950 border border-slate-700 px-3 py-1.5 text-[11px] font-mono text-slate-200"
                            value={inviteLink}
                            readOnly
                          />
                        </div>
                        <div className="flex items-center gap-2">
                          <button
                            onClick={() => copyInviteLink(room)}
                            className="px-3 py-1 rounded-full border border-slate-600 text-slate-200 text-[11px] hover:border-sky-500 hover:text-sky-300"
                          >
                            Скопировать
                          </button>
                        </div>
                      </div>
                      <div className="text-[10px] text-slate-500 mt-1">
                        Отправь эту ссылку в чат группы, рассылку или личные сообщения.
                        Участники переходят по ссылке, вводят своё имя и попадают в комнату.
                      </div>
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </section>
    </div>
  )
}
