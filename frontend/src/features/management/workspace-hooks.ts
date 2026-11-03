import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useOutletContext } from "react-router-dom";
import type { DemoApi } from "./demo-api";
import type { Workspace } from "./types";

export interface WorkspaceContext {
  workspace: Workspace;
  api: DemoApi;
  queryKey: readonly string[];
  notify: (title: string, description?: string) => void;
}

export const useWorkspace = () => useOutletContext<WorkspaceContext>();

export function useWorkspaceMutation<TInput, TResult>(
  action: (api: DemoApi, input: TInput) => Promise<TResult>,
) {
  const { api, queryKey } = useWorkspace();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: TInput) => action(api, input),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey });
    },
  });
}
