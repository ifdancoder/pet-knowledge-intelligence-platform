import type { Conversation } from '../../domain/conversations/types'

interface ConversationListProps {
  conversations: Conversation[]
  activeConversationId: string | null
  onSelect: (conversationId: string) => void
}

export function ConversationList({ conversations, activeConversationId, onSelect }: ConversationListProps) {
  return (
    <ul className="flex flex-col gap-1">
      {conversations.map((conversation) => (
        <li key={conversation.id}>
          <button
            onClick={() => onSelect(conversation.id)}
            className={`w-full rounded-lg px-3 py-2 text-left text-sm transition-colors ${
              conversation.id === activeConversationId
                ? 'bg-accent text-background'
                : 'text-text-secondary hover:bg-surface'
            }`}
          >
            {conversation.id}
          </button>
        </li>
      ))}
    </ul>
  )
}
