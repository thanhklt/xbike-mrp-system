import { useRef } from "react";
import { useWrite } from "./api/useResources.js";
import { useFeedback } from "../components/FeedbackProvider.jsx";
export function useSave() {
  const mutation = useWrite();
  const pending = useRef(false);
  const { notify } = useFeedback();
  async function save(options, onSaved) {
    if (pending.current) return;
    pending.current = true;
    try {
      const result = await mutation.mutateAsync(options);
      notify("Đã lưu thay đổi.");
      onSaved?.(result);
    } catch {
      /* The mutation error is displayed beside the form; never retry writes automatically. */
    } finally {
      pending.current = false;
    }
  }
  return { save, busy: mutation.isPending, error: mutation.error };
}
