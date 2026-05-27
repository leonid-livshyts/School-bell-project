// TS mirror of backend pydantic models. Datetimes come as ISO strings.

export interface Lesson {
  id: number
  name: string
  start: string
  end: string
  room_id: number
  created_at?: string
  updated_at?: string
}

export interface LessonInput {
  name: string
  start: string
  end: string
  room_id: number
}

export interface Room {
  id: number
  name: string
  created_at?: string
  updated_at?: string
}

export interface RoomInput {
  name: string
}

export interface Alarm {
  id: number
  is_active: boolean
  room_id: number
  created_at?: string
  updated_at?: string
}

export interface Measure {
  id: number
  temperature: number | null
  humidity: number | null
  volume: number | null
  air_quality: number | null
  measure_time: string
  room_id: number
}

export interface MeasureInput {
  temperature?: number
  humidity?: number
  volume?: number
  air_quality?: number
  measure_timestamp: number
}

export interface Device {
  id: number
  key: string
  version: string
  installed_date: string
  room_id: number
  created_at?: string
  updated_at?: string
}

export interface DeviceInput {
  key: string
  version: string
  installed_date: string
}

export interface VoiceMessage {
  id: number
  filename: string
  room_id: number | null
  created_at?: string
  updated_at?: string
}

export interface Ringtone {
  id: number
  filename: string
  room_id: number | null
  created_at?: string
  updated_at?: string
}

export interface LoginResponse {
  access_token: string
  token_type: "bearer"
}

export interface RegisterInput {
  username: string
  password1: string
  password2: string
  email: string | null
  role: string | null
}
