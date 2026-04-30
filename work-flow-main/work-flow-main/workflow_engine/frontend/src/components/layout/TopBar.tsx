import { useRef } from "react";
import type { ChangeEvent } from "react";
import type { WorkflowDefinition } from "../../types/workflow";
import { Button } from "../ui/button";
import { Input } from "../ui/input";

interface TopBarProps {
  workflowName: string;
  versionStatus: "saved" | "unsaved";
  isSaving: boolean;
  isExecuting: boolean;
  onWorkflowNameChange: (name: string) => void;
  onSave: () => void;
  onExecute: () => void;
  onStop: () => void;
  onImportWorkflow: (workflow: WorkflowDefinition) => void;
  onExportWorkflow: () => void;
}

export const TopBar = ({
  workflowName,
  versionStatus,
  isSaving,
  isExecuting,
  onWorkflowNameChange,
  onSave,
  onExecute,
  onStop,
  onImportWorkflow,
  onExportWorkflow,
}: TopBarProps) => {
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const handleImportClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) {
      return;
    }

    const text = await file.text();
    const parsed = JSON.parse(text) as WorkflowDefinition;
    onImportWorkflow(parsed);
  };

  return (
    <header className="flex h-14 items-center gap-3 border-b border-border bg-card px-4">
      <div className="w-72">
        <Input value={workflowName} onChange={(event) => onWorkflowNameChange(event.target.value)} />
      </div>

      <div className="text-xs text-slate-500">
        版本状态：{versionStatus === "saved" ? "已保存" : "未保存"}
      </div>

      <div className="ml-auto flex items-center gap-2">
        <Button variant="outline" onClick={onSave} disabled={isSaving}>
          {isSaving ? "保存中..." : "保存"}
        </Button>
        <Button onClick={onExecute} disabled={isExecuting}>
          {isExecuting ? "执行中..." : "执行"}
        </Button>
        <Button variant="secondary" onClick={onStop} disabled>
          停止
        </Button>
        <Button variant="outline" onClick={handleImportClick}>
          导入
        </Button>
        <Button variant="outline" onClick={onExportWorkflow}>
          导出
        </Button>
      </div>

      <input
        ref={fileInputRef}
        type="file"
        className="hidden"
        accept="application/json,.json"
        onChange={handleFileChange}
      />
    </header>
  );
};