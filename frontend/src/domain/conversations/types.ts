export interface Conversation {
  id: string
}

export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  sourceChunkIds: string[]
}
