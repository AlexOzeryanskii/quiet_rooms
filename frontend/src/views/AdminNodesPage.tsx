import React, { useEffect, useState } from 'react'
import { api, API_BASE_URL } from '../api/http'

interface NodeItem {
  id: string
  name: string
  base_url: string
  status: string
  active_rooms: number
  max_rooms: number
  last_heartbeat?: string
}

interface CreateNodeForm {
  name: string
  base_url: string
  max_rooms: number
  api_key: string
}

export const AdminNodesPage: React.FC = () => {
  const [nodes, setNodes] = useState<NodeItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [form, setForm] = useState<CreateNodeForm>({
    name: '',
    base_url: '',
    max_rooms: 3,
    api_key: '',
  })

  const [creating, setCreating] = useState(false)
  const [openScriptId, setOpenScriptId] = useState<string | null>(null)
  const [openSystemdId, setOpenSystemdId] = useState<string | null>(null)

  const loadNodes = async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await api.get<NodeItem[]>('/nodes/')
      setNodes(res.data || [])
    } catch (e: any) {
      console.error(e)
      setError(e?.response?.data?.detail || 'Не удалось загрузить список нод')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadNodes()
  }, [])

  const handleChange = (field: keyof CreateNodeForm, value: string | number) => {
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
      const payload: any = {
        name: form.name,
        base_url: form.base_url,
        max_rooms: form.max_rooms,
      }
      if (form.api_key.trim()) {
        payload.api_key = form.api_key.trim()
      }

      const res = await api.post<NodeItem>('/nodes/', payload)
      setNodes((prev) => [res.data, ...prev])

      setForm({
        name: '',
        base_url: '',
        max_rooms: 3,
        api_key: '',
      })
    } catch (e: any) {
      console.error(e)
      setError(e?.response?.data?.detail || 'Не удалось создать ноду')
    } finally {
      setCreating(false)
    }
  }

  const formatDateTime = (iso?: string) => {
    if (!iso) return '—'
    const d = new Date(iso)
    if (isNaN(d.getTime())) return iso
    return d.toLocaleString()
  }

  const getPortFromBaseUrl = (baseUrl: string): string => {
    try {
      const u = new URL(baseUrl)
      if (u.port) return u.port
      // если порт не указан — по умолчанию 9000
      return '9000'
    } catch {
      return '9000'
    }
  }

  const getInstallScript = (node: NodeItem) => {
    const shortId = node.id.slice(0, 8)
    const port = getPortFromBaseUrl(node.base_url)

    return `#!/bin/bash
# Quiet Rooms — установка ноды "${node.name}"

# 1. Обновление системы и установка зависимостей
sudo apt update && sudo apt install -y python3 python3-venv python3-pip git

# 2. Каталог для ноды
sudo mkdir -p /opt/quiet_node_${shortId}
sudo chown $USER:$USER /opt/quiet_node_${shortId}
cd /opt/quiet_node_${shortId}

# 3. Клонировать репозиторий проекта (ЗАМЕНИ на свой репозиторий)
git clone YOUR_REPO_URL_HERE .

# 4. Виртуальное окружение и зависимости
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r node_service/requirements.txt

# 5. Настройка .env для ноды
cat > node_service/.env << 'EOF'
NODE_ID=${node.id}
CONTROL_PLANE_URL=${API_BASE_URL}
HEARTBEAT_INTERVAL_SECONDS=10
EOF

# 6. Тестовый запуск узла (убедиться, что все работает)
uvicorn node_service.app.main:app --host 0.0.0.0 --port ${port}
`
  }

  const getSystemdUnit = (node: NodeItem) => {
    const shortId = node.id.slice(0, 8)
    const port = getPortFromBaseUrl(node.base_url)

    return `# Сохранить в /etc/systemd/system/quiet-node-${shortId}.service
[Unit]
Description=Quiet Rooms Node ${node.name}
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/opt/quiet_node_${shortId}
Environment="PYTHONUNBUFFERED=1"
# .env в node_service/.env будет прочитан через настройки приложения
ExecStart=/opt/quiet_node_${shortId}/.venv/bin/uvicorn node_service.app.main:app --host 0.0.0.0 --port ${port}
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target

# Команды:
# sudo systemctl daemon-reload
# sudo systemctl enable quiet-node-${shortId}
# sudo systemctl start quiet-node-${shortId}
# sudo systemctl status quiet-node-${shortId}
`
  }

  return (
    <div className="space-y-6">
      <section className="bg-slate-900 border border-slate-800 rounded-2xl p-4">
        <h1 className="text-xl font-semibold mb-2">Админка: сервера-ноды</h1>
        <p className="text-sm text-slate-400 max-w-2xl">
          Здесь ты управляешь арендными серверами. Каждая нода — это отдельный сервер, на
          котором крутится node_service и обрабатывает комнаты. Создаёшь запись ноды, копируешь
          готовые скрипты, запускаешь их на сервере — и нода начинает отправлять heartbeat.
        </p>
      </section>

      <section className="bg-slate-900 border border-slate-800 rounded-2xl p-4">
        <h2 className="text-lg font-semibold mb-3">Создать новую ноду</h2>
        <form onSubmit={handleCreate} className="space-y-3">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div>
              <label className="block text-xs text-slate-400 mb-1">Название ноды</label>
              <input
                className="w-full rounded-lg bg-slate-950 border border-slate-700 px-3 py-2 text-sm focus:outline-none focus:border-sky-500"
                placeholder="prod-node-1 / eu-1 / asia-1"
                value={form.name}
                onChange={(e) => handleChange('name', e.target.value)}
                required
              />
            </div>
            <div>
              <label className="block text-xs text-slate-400 mb-1">
                Базовый URL ноды (для control-plane и фронта)
              </label>
              <input
                className="w-full rounded-lg bg-slate-950 border border-slate-700 px-3 py-2 text-sm focus:outline-none focus:border-sky-500"
                placeholder="http://123.123.123.123:9000"
                value={form.base_url}
                onChange={(e) => handleChange('base_url', e.target.value)}
                required
              />
            </div>
            <div>
              <label className="block text-xs text-slate-400 mb-1">
                Максимум одновременных комнат на ноде
              </label>
              <input
                type="number"
                min={1}
                className="w-full rounded-lg bg-slate-950 border border-slate-700 px-3 py-2 text-sm focus:outline-none focus:border-sky-500"
                value={form.max_rooms}
                onChange={(e) =>
                  handleChange('max_rooms', Number(e.target.value) || 1)
                }
              />
            </div>
            <div>
              <label className="block text-xs text-slate-400 mb-1">
                API ключ ноды (опционально)
              </label>
              <input
                className="w-full rounded-lg bg-slate-950 border border-slate-700 px-3 py-2 text-sm focus:outline-none focus:border-sky-500"
                placeholder="prod-node-1-secret (если используешь auth на ноде)"
                value={form.api_key}
                onChange={(e) => handleChange('api_key', e.target.value)}
              />
            </div>
          </div>
          {error && <div className="text-xs text-red-400">{error}</div>}
          <div className="flex items-center gap-3 pt-1">
            <button
              type="submit"
              disabled={creating}
              className="px-4 py-2 rounded-lg bg-sky-600 hover:bg-sky-500 text-sm font-medium disabled:opacity-60"
            >
              {creating ? 'Создаём...' : 'Создать ноду'}
            </button>
            <span className="text-xs text-slate-500">
              После создания открой скрипты для установки и systemd, вставь их на свой сервер.
            </span>
          </div>
        </form>
      </section>

      <section className="bg-slate-900 border border-slate-800 rounded-2xl p-4">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-lg font-semibold">Список нод</h2>
          {loading && <span className="text-xs text-slate-500">Обновляем...</span>}
        </div>
        {nodes.length === 0 && !loading ? (
          <div className="text-sm text-slate-500">
            Пока ни одной ноды. Создай первую — она станет первым арендным сервером для комнат.
          </div>
        ) : (
          <div className="space-y-2">
            {nodes.map((node) => {
              const installScript = getInstallScript(node)
              const systemdUnit = getSystemdUnit(node)
              const isOnline =
                node.status === 'active' || node.status === 'online'

              return (
                <div
                  key={node.id}
                  className="bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-sm"
                >
                  <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
                    <div>
                      <div className="font-medium text-slate-100">
                        {node.name}{' '}
                        <span className="text-xs text-slate-500">
                          ({node.id.slice(0, 8)})
                        </span>
                      </div>
                      <div className="text-xs text-slate-400">
                        URL ноды:{' '}
                        <span className="font-mono text-slate-300">
                          {node.base_url}
                        </span>
                      </div>
                      <div className="text-[11px] text-slate-500">
                        Комнат: {node.active_rooms} / {node.max_rooms} · последнее
                        сердце: {formatDateTime(node.last_heartbeat)}
                      </div>
                    </div>
                    <div className="flex flex-wrap items-center gap-2">
                      <span
                        className={
                          'px-2 py-0.5 rounded-full text-[11px] border ' +
                          (isOnline
                            ? 'border-emerald-400 text-emerald-300'
                            : 'border-slate-700 text-slate-500')
                        }
                      >
                        {isOnline ? 'Онлайн' : 'Офлайн'}
                      </span>
                      <button
                        onClick={() =>
                          setOpenScriptId((prev) =>
                            prev === node.id ? null : node.id
                          )
                        }
                        className="px-3 py-1 rounded-full border border-sky-600 text-sky-300 hover:bg-sky-600 hover:text-white text-xs"
                      >
                        {openScriptId === node.id
                          ? 'Скрыть установку'
                          : 'Скрипт установки'}
                      </button>
                      <button
                        onClick={() =>
                          setOpenSystemdId((prev) =>
                            prev === node.id ? null : node.id
                          )
                        }
                        className="px-3 py-1 rounded-full border border-slate-600 text-slate-300 hover:border-emerald-500 hover:text-emerald-300 text-xs"
                      >
                        {openSystemdId === node.id
                          ? 'Скрыть systemd'
                          : 'systemd-сервис'}
                      </button>
                    </div>
                  </div>

                  {openScriptId === node.id && (
                    <div className="mt-3">
                      <div className="text-[11px] text-slate-400 mb-1">
                        1) Подключаешься к арендному серверу по SSH.
                        2) Вставляешь этот скрипт целиком и запускаешь.
                        3) Проверяешь, что /health и heartbeat работают.
                      </div>
                      <textarea
                        className="w-full text-[11px] font-mono bg-slate-950 border border-slate-700 rounded-lg p-2 text-slate-200"
                        rows={12}
                        value={installScript}
                        readOnly
                      />
                    </div>
                  )}

                  {openSystemdId === node.id && (
                    <div className="mt-3">
                      <div className="text-[11px] text-slate-400 mb-1">
                        После того как нода успешно запустилась вручную:
                        <br />
                        1) Создай unit-файл на сервере
                        <span className="font-mono text-slate-300">
                          sudo nano /etc/systemd/system/quiet-node-{node.id.slice(0, 8)}.service
                        </span>
                        <br />
                        2) Вставь туда этот текст, сохрани.
                        3) Выполни команды из нижних комментариев (daemon-reload, enable, start).
                      </div>
                      <textarea
                        className="w-full text-[11px] font-mono bg-slate-950 border border-slate-700 rounded-lg p-2 text-slate-200"
                        rows={14}
                        value={systemdUnit}
                        readOnly
                      />
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        )}
      </section>
    </div>
  )
}
