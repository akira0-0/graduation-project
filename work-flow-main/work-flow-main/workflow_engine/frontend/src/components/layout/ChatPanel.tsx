import { useMemo } from "react";
import type { ChatMessage, WorkflowListItem } from "../../types/workflow";
import { Button } from "../ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "../ui/card";
import { Textarea } from "../ui/textarea";

interface ChatPanelProps {
  messages: ChatMessage[];
  chatInput: string;
  chatLoading: boolean;
  quickEntryLoading: boolean;
  workflowList: WorkflowListItem[];
  conversationId: string | null;
  workflowId: string | null;
  hasPendingWorkflow: boolean;
  onLoadWorkflow: (workflowId: string) => void;
  onChatInputChange: (value: string) => void;
  onSendMessage: () => void;
  onApplyToCanvas: () => void;
  onQuickPublicOpinion: () => void;
}

const roleText: Record<ChatMessage["role"], string> = {
  user: "用户",
  assistant: "助手",
  system: "系统",
};

export const ChatPanel = ({
  messages,
  chatInput,
  chatLoading,
  quickEntryLoading,
  workflowList,
  conversationId,
  workflowId,
  hasPendingWorkflow,
  onLoadWorkflow,
  onChatInputChange,
  onSendMessage,
  onApplyToCanvas,
  onQuickPublicOpinion,
}: ChatPanelProps) => {
  const latestWorkflows = useMemo(() => workflowList.slice(0, 10), [workflowList]);

  return (
    <aside className="flex h-full w-[30%] min-w-[320px] flex-col border-r border-border bg-card">
      <Card className="m-3 mb-2">
        <CardHeader className="pb-2">
          <CardTitle>会话信息</CardTitle>
        </CardHeader>
        <CardContent className="space-y-1 text-xs text-slate-600">
          <div>会话ID：{conversationId ?? "-"}</div>
          <div>工作流ID：{workflowId ?? "-"}</div>
          <div className="space-y-2 pt-2">
            <Button
              className="w-full"
              variant="outline"
              onClick={onApplyToCanvas}
              disabled={!hasPendingWorkflow || quickEntryLoading}
            >
              应用到画布
            </Button>
            <Button className="w-full" onClick={onQuickPublicOpinion} disabled={quickEntryLoading}>
              {quickEntryLoading ? "舆情分析生成中..." : "舆情分析快捷入口"}
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card className="mx-3 mb-2">
        <CardHeader className="pb-2">
          <CardTitle>已有工作流</CardTitle>
        </CardHeader>
        <CardContent className="max-h-40 overflow-auto text-xs">
          {latestWorkflows.length === 0 ? (
            <div className="text-slate-500">暂无记录</div>
          ) : (
            <ul className="space-y-2">
              {latestWorkflows.map((item) => (
                <li
                  key={item.id}
                  className="cursor-pointer rounded-md border border-border p-2 transition-colors hover:border-primary hover:bg-accent"
                  onClick={() => onLoadWorkflow(item.id)}
                  onKeyDown={(event) => {
                    if (event.key === "Enter" || event.key === " ") {
                      onLoadWorkflow(item.id);
                    }
                  }}
                  tabIndex={0}
                  role="button"
                >
                  <div className="truncate text-sm font-medium">{item.name}</div>
                  <div className="truncate text-[11px] text-slate-500">{item.id}</div>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>

      <div className="mx-3 mb-2 flex-1 space-y-2 overflow-auto rounded-md border border-border bg-background p-2">
        {messages.map((message) => (
          <div key={message.id} className="rounded-md border border-border bg-card p-2">
            <div className="mb-1 text-[11px] font-semibold text-slate-500">{roleText[message.role]}</div>
            <div className="whitespace-pre-wrap text-sm">{message.content}</div>
          </div>
        ))}
      </div>

      <div className="m-3 mt-1 space-y-2">
        <Textarea
          value={chatInput}
          onChange={(event) => onChatInputChange(event.target.value)}
          rows={4}
          placeholder="输入需求，首次调用 start，后续调用 continue"
        />
        <Button className="w-full" onClick={onSendMessage} disabled={chatLoading || !chatInput.trim()}>
          {chatLoading ? "发送中..." : "发送"}
        </Button>
      </div>
    </aside>
  );
};