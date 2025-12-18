/*
  QUIET ROOMS — ROOM PAGE
  Версия стабильная, с рабочим чатом, видео, fullscreen, контролем прав.
*/

import React, { useEffect, useRef, useState } from "react"
import { useNavigate, useParams } from "react-router-dom"
import { api } from "../api/http"
import { useAuth } from "../auth/AuthContext"

/* ------------------------
   Типы сообщений и структур
--------------------------- */

interface RoomNodeInfo {
  node_base_url: string
  room_code: string
}

interface RoomInfo {
  id: string
  code: string
  title: string | null
  owner_id: string
  max_participants: number
  status: string
}

interface Participant {
  id: string
  name: string
  isYou?: boolean
  isSpeaking?: boolean
  hasVideo?: boolean
}

interface WsParticipantsMessage {
  type: "participants"
  participants: { id: string; name: string }[]
}

interface WsSignalMessage {
  type: "signal"
  from: string
  to: string
  signalType: "offer" | "answer" | "ice"
  payload: any
}

interface WsControlMessage {
  type: "control"
  from: string
  to?: string
  action: string
  payload?: any
}

interface WsChatMessage {
  type: "chat"
  from: string
  name: string
  text: string
  ts: string
}

interface ChatMessage {
  fromId: string
  fromName: string
  text: string
  ts: string
  isOwn: boolean
}

const iceConfig: RTCConfiguration = {
  iceServers: [{ urls: "stun:stun.l.google.com:19302" }],
}

/* ------------------------
   Компонент RoomPage
--------------------------- */

export const RoomPage: React.FC = () => {
  const { code } = useParams<{ code: string }>()
  const { user } = useAuth()
  const navigate = useNavigate()

  const [info, setInfo] = useState<RoomNodeInfo | null>(null)
  const [room, setRoom] = useState<RoomInfo | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [blocked, setBlocked] = useState(false)

  const [participants, setParticipants] = useState<Participant[]>([])
  const [isMuted, setIsMuted] = useState(true)
  const [videoAllowed, setVideoAllowed] = useState(false)
  const [quietMode, setQuietMode] = useState(true)
  const [handRaised, setHandRaised] = useState(false)
  const [isFullscreen, setIsFullscreen] = useState(false)

  const videoContainerRef = useRef<HTMLDivElement | null>(null)

  const wsRef = useRef<WebSocket | null>(null)
  const clientIdRef = useRef<string>("")

  const peerConnectionsRef = useRef<Map<string, RTCPeerConnection>>(new Map())
  const localStreamRef = useRef<MediaStream | null>(null)
  const remoteStreamsRef = useRef<Map<string, MediaStream>>(new Map())

  const localVideoRef = useRef<HTMLVideoElement | null>(null)
  const remoteVideoRef = useRef<HTMLVideoElement | null>(null)

  const displayName = user?.email || "Гость"
  const isHost = room && user && room.owner_id == user.id

  /* ------------------------
     Чат
  --------------------------- */
  const [showChat, setShowChat] = useState(true)
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([])
  const [chatInput, setChatInput] = useState("")
  const chatEndRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [chatMessages])

  /* ------------------------
     Fullscreen handler
  --------------------------- */
  useEffect(() => {
    const handler = () => {
      if (!document.fullscreenElement) setIsFullscreen(false)
    }
    document.addEventListener("fullscreenchange", handler)
    return () => document.removeEventListener("fullscreenchange", handler)
  }, [])

  const toggleFullscreen = async () => {
    const el = videoContainerRef.current
    if (!el) return
    if (!document.fullscreenElement) {
      await el.requestFullscreen()
      setIsFullscreen(true)
    } else {
      await document.exitFullscreen()
      setIsFullscreen(false)
    }
  }

  /* ------------------------
     Загрузка инфы о комнате
  --------------------------- */

  useEffect(() => {
    if (!code) return
    ;(async () => {
      try {
        const node = await api.get(`/rooms/${code}/node`)
        setInfo(node.data)
      } catch (e: any) {
        setError("Комната не найдена")
      }
      try {
        const r = await api.get(`/rooms/${code}`)
        setRoom(r.data)
      } catch {
        /* гость — норм */
      }
      setLoading(false)
    })()
  }, [code])

  /* ------------------------
     WebRTC peer helpers
  --------------------------- */

  const createPeerConnection = (remoteId: string) => {
    let pc = peerConnectionsRef.current.get(remoteId)
    if (pc) return pc

    pc = new RTCPeerConnection(iceConfig)

    pc.onicecandidate = (event) => {
      if (event.candidate && wsRef.current) {
        wsRef.current.send(
          JSON.stringify({
            type: "signal",
            from: clientIdRef.current,
            to: remoteId,
            signalType: "ice",
            payload: event.candidate,
          }),
        )
      }
    }

    pc.ontrack = (event) => {
      const stream = event.streams[0]
      if (!stream) return
      remoteStreamsRef.current.set(remoteId, stream)
      updateRemoteVideo()
      updateParticipant(remoteId, { hasVideo: true })
    }

    if (localStreamRef.current) {
      localStreamRef.current.getTracks().forEach((track) => {
        pc!.addTrack(track, localStreamRef.current!)
      })
    }

    peerConnectionsRef.current.set(remoteId, pc)
    return pc
  }

  const updateParticipant = (id: string, data: Partial<Participant>) => {
    setParticipants((prev) =>
      prev.map((p) => (p.id === id ? { ...p, ...data } : p)),
    )
  }

  const updateRemoteVideo = () => {
    const streams = Array.from(remoteStreamsRef.current.values())
    remoteVideoRef.current!.srcObject = streams[0] ?? null
  }

  const startConnection = async (remoteId: string) => {
    if (remoteId === clientIdRef.current) return
    const pc = createPeerConnection(remoteId)
    if (clientIdRef.current < remoteId) {
      const offer = await pc.createOffer()
      await pc.setLocalDescription(offer)
      wsRef.current?.send(
        JSON.stringify({
          type: "signal",
          from: clientIdRef.current,
          to: remoteId,
          signalType: "offer",
          payload: offer,
        }),
      )
    }
  }

  /* ------------------------
     Подключение по WebSocket
  --------------------------- */

  useEffect(() => {
    if (!info) return

    const clientId =
      crypto.randomUUID?.() ||
      `${Date.now()}-${Math.random().toString(16).slice(2)}`
    clientIdRef.current = clientId

    const base = new URL(info.node_base_url)
    const proto = base.protocol === "https:" ? "wss:" : "ws:"
    const wsURL = `${proto}//${base.host}/ws/rooms/${info.room_code}?client_id=${clientId}&name=${encodeURIComponent(
      displayName,
    )}`

    const ws = new WebSocket(wsURL)
    wsRef.current = ws

    ws.onmessage = async (event) => {
      let data: any
      try {
        data = JSON.parse(event.data)
      } catch {
        return
      }

      if (data.type === "participants") {
        const msg = data as WsParticipantsMessage
        setParticipants(
          msg.participants.map((p) => ({
            id: p.id,
            name: p.name,
            isYou: p.id === clientIdRef.current,
          })),
        )
        for (const p of msg.participants) {
          if (p.id !== clientIdRef.current) startConnection(p.id)
        }
      }

      else if (data.type === "signal") {
        const msg = data as WsSignalMessage
        if (msg.to !== clientIdRef.current) return
        const pc = createPeerConnection(msg.from)
        if (msg.signalType === "offer") {
          await pc.setRemoteDescription(msg.payload)
          const answer = await pc.createAnswer()
          await pc.setLocalDescription(answer)
          ws.send(
            JSON.stringify({
              type: "signal",
              from: clientIdRef.current,
              to: msg.from,
              signalType: "answer",
              payload: answer,
            }),
          )
        } else if (msg.signalType === "answer") {
          await pc.setRemoteDescription(msg.payload)
        } else if (msg.signalType === "ice") {
          try {
            await pc.addIceCandidate(msg.payload)
          } catch {}
        }
      }

      else if (data.type === "control") {
        const msg = data as WsControlMessage
        if (!msg.to || msg.to === clientIdRef.current) {
          if (msg.action === "video_permission") {
            setVideoAllowed(Boolean(msg.payload?.allowed))
            if (!msg.payload?.allowed) disableMedia()
          }
          if (msg.action === "block") {
            setBlocked(true)
            ws.close()
            setTimeout(() => navigate("/dashboard"), 1500)
          }
        }
      }

      else if (data.type === "chat") {
        const msg = data as WsChatMessage
        if (msg.from === clientIdRef.current) return // не дублируем свои

        setChatMessages((prev) => [
          ...prev,
          {
            fromId: msg.from,
            fromName: msg.name,
            text: msg.text,
            ts: msg.ts,
            isOwn: false,
          },
        ])
      }
    }

    ws.onclose = () => {
      wsRef.current = null
    }

    return () => {
      ws.close()
      peerConnectionsRef.current.forEach((pc) => pc.close())
      peerConnectionsRef.current.clear()
    }
  }, [info])

  /* ------------------------
     Управление медиа
  --------------------------- */

  const enableMedia = async () => {
    const stream = await navigator.mediaDevices.getUserMedia({
      video: true,
      audio: true,
    })
    localStreamRef.current = stream
    if (localVideoRef.current) localVideoRef.current.srcObject = stream
    setIsMuted(false)

    peerConnectionsRef.current.forEach((pc) => {
      stream.getTracks().forEach((t) => pc.addTrack(t, stream))
    })
  }

  const disableMedia = () => {
    const s = localStreamRef.current
    if (s) s.getTracks().forEach((t) => t.stop())
    localStreamRef.current = null
    if (localVideoRef.current) localVideoRef.current.srcObject = null
    setIsMuted(true)
  }

  const toggleMedia = async () => {
    if (!videoAllowed && !isHost) return
    if (localStreamRef.current) disableMedia()
    else await enableMedia()
  }

  const toggleMute = () => {
    if (!localStreamRef.current) return
    const track = localStreamRef.current.getAudioTracks()[0]
    if (!track) return
    track.enabled = !track.enabled
    setIsMuted(!track.enabled)
  }

  const sendVideoPermission = (id: string, allowed: boolean) => {
    wsRef.current?.send(
      JSON.stringify({
        type: "control",
        from: clientIdRef.current,
        to: id,
        action: "video_permission",
        payload: { allowed },
      }),
    )
  }

  const blockParticipant = (id: string) => {
    wsRef.current?.send(
      JSON.stringify({
        type: "control",
        action: "block",
        from: clientIdRef.current,
        to: id,
      }),
    )
  }

  /* ------------------------
     Чат: отправка
  --------------------------- */

  const sendChat = (e: React.FormEvent) => {
    e.preventDefault()
    const text = chatInput.trim()
    if (!text) return

    // Локально
    const localMessage: ChatMessage = {
      fromId: clientIdRef.current,
      fromName: displayName,
      text,
      ts: new Date().toISOString(),
      isOwn: true,
    }
    setChatMessages((prev) => [...prev, localMessage])
    setChatInput("")

    wsRef.current?.send(
      JSON.stringify({
        type: "chat",
        text,
        name: displayName,
      }),
    )
  }

  /* ------------------------
     Рендер страницы
  --------------------------- */

  if (loading) return <div className="text-slate-200">Загрузка...</div>
  if (error) return <div className="text-red-400">{error}</div>
  if (!info) return null

  if (blocked)
    return (
      <div className="text-center text-red-400 mt-10">
        Вы были отключены ведущим
      </div>
    )

  return (
    <div className="grid grid-cols-1 md:grid-cols-[3fr_1.2fr] gap-4">
      {/* ---------------------- VIDEO BLOCK ---------------------- */}
      <div
        ref={videoContainerRef}
        className="bg-slate-900 border border-slate-800 rounded-2xl p-3 flex flex-col"
      >
        {/* Верхняя панель */}
        <div className="flex items-center justify-between text-xs text-slate-400 mb-2">
          <div>
            Комната{" "}
            <span className="font-mono text-slate-100">{info.room_code}</span>
            <div className="text-[10px] text-slate-600">
              {isHost
                ? "Вы — ведущий"
                : videoAllowed
                ? "Вам разрешено включить видео"
                : "Видео доступно по разрешению ведущего"}
            </div>
          </div>
          <button
            onClick={toggleFullscreen}
            className="px-2 py-1 border border-slate-700 rounded-lg text-slate-300 hover:border-sky-500"
          >
            {isFullscreen ? "Обычный режим" : "На весь экран"}
          </button>
        </div>

        {/* Само видео */}
        <div className="flex-1 bg-black rounded-xl border border-slate-800 flex items-center justify-center relative overflow-hidden">
          <video
            ref={remoteVideoRef}
            className="w-full h-full object-contain"
            autoPlay
            playsInline
          />
          {localStreamRef.current && (
            <video
              ref={localVideoRef}
              muted
              autoPlay
              playsInline
              className="absolute bottom-2 right-2 w-32 h-24 rounded-lg border border-slate-700 object-cover"
            />
          )}
        </div>

        {/* Нижняя панель кнопок */}
        <div className="flex items-center gap-2 mt-3 flex-wrap text-xs">
          <button
            onClick={toggleMedia}
            className="px-3 py-1 border border-slate-600 rounded-full text-slate-200"
          >
            {localStreamRef.current
              ? "Выключить камеру"
              : "Включить камеру"}
          </button>

          <button
            onClick={toggleMute}
            disabled={!localStreamRef.current}
            className="px-3 py-1 border border-slate-600 rounded-full text-slate-200 disabled:opacity-50"
          >
            {isMuted ? "Микрофон выкл." : "Микрофон вкл."}
          </button>

          <button
            onClick={() => setHandRaised(!handRaised)}
            className={
              "px-3 py-1 border rounded-full " +
              (handRaised
                ? "border-sky-500 text-sky-300"
                : "border-slate-600 text-slate-300")
            }
          >
            {handRaised ? "Рука поднята" : "Поднять руку"}
          </button>

          <button
            onClick={() => setQuietMode(!quietMode)}
            className="px-3 py-1 border border-slate-600 rounded-full text-slate-200"
          >
            {quietMode ? "Тихий режим" : "Обсуждение"}
          </button>

          <button
            onClick={() => {
              wsRef.current?.close()
              navigate("/dashboard")
            }}
            className="ml-auto px-3 py-1 bg-red-600 text-white rounded-full"
          >
            Выйти
          </button>
        </div>
      </div>

      {/* ---------------------- RIGHT PANEL ---------------------- */}

      <aside className="bg-slate-900 border border-slate-800 rounded-2xl p-3 flex flex-col">
        {/* Участники */}
        <h2 className="text-sm font-semibold mb-2 text-slate-200">
          Участники ({participants.length})
        </h2>

        <div className="flex-1 overflow-auto mb-3 space-y-1 pr-1">
          {participants.map((p) => (
            <div
              key={p.id}
              className={
                "flex items-center justify-between rounded-lg px-2 py-1 " +
                (p.isYou ? "bg-slate-800" : "bg-slate-950")
              }
            >
              <div>
                <div className="text-slate-100 text-xs">
                  {p.name}
                  {p.isYou && (
                    <span className="text-sky-400 ml-1">(вы)</span>
                  )}
                </div>
              </div>

              {/* Только ведущему — кнопки управления */}
              {isHost && !p.isYou && (
                <div className="flex gap-1 text-[10px]">
                  <button
                    onClick={() => sendVideoPermission(p.id, true)}
                    className="px-2 py-0.5 border border-slate-600 rounded text-slate-300"
                  >
                    Разрешить видео
                  </button>
                  <button
                    onClick={() => sendVideoPermission(p.id, false)}
                    className="px-2 py-0.5 border border-slate-600 rounded text-slate-300"
                  >
                    Запретить
                  </button>
                  <button
                    onClick={() => blockParticipant(p.id)}
                    className="px-2 py-0.5 border border-red-600 text-red-300 rounded"
                  >
                    Блок
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>

        {/* ЧАТ */}
        <div className="border-t border-slate-800 pt-2">
          <div className="flex items-center justify-between mb-1">
            <h3 className="text-xs font-semibold text-slate-200">Чат</h3>
            <button
              onClick={() => setShowChat(!showChat)}
              className="text-slate-400 text-[11px]"
            >
              {showChat ? "Скрыть" : "Показать"}
            </button>
          </div>

          {showChat && (
            <div className="flex flex-col gap-2">
              <div className="border border-slate-700 rounded-lg bg-slate-950 p-2 max-h-64 overflow-auto">
                {chatMessages.map((m, i) => (
                  <div
                    key={i}
                    className={
                      "mb-1 flex " + (m.isOwn ? "justify-end" : "justify-start")
                    }
                  >
                    <div
                      className={
                        "px-2 py-1 rounded-lg max-w-[80%] text-xs " +
                        (m.isOwn
                          ? "bg-sky-700 text-slate-100"
                          : "bg-slate-800 text-slate-200")
                      }
                    >
                      <div className="text-[10px] text-slate-400 mb-1">
                        {m.isOwn ? "Вы" : m.fromName}
                      </div>
                      {m.text}
                    </div>
                  </div>
                ))}
                <div ref={chatEndRef} />
              </div>

              <form onSubmit={sendChat} className="flex gap-1">
                <input
                  value={chatInput}
                  onChange={(e) => setChatInput(e.target.value)}
                  className="flex-1 bg-slate-950 border border-slate-700 px-2 py-1 rounded-lg text-xs text-slate-100 focus:border-sky-500"
                  placeholder="Сообщение..."
                />
                <button
                  type="submit"
                  className="px-3 py-1 bg-sky-600 text-white rounded-lg text-xs"
                >
                  Отпр.
                </button>
              </form>
            </div>
          )}
        </div>
      </aside>
    </div>
  )
}
