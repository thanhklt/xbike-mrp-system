import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { readAll, readResource, writeResource } from "./client.js";
import { API } from "./endpoints.js";
import { useAuth } from "../../features/auth/AuthProvider.jsx";

export function useResource(path, params = {}, enabled = true) {
  const { user } = useAuth();
  return useQuery({
    queryKey: ["resources", user?.id, user?.ma_vai_tro, path, params],
    queryFn: ({ signal }) => readResource(path, params, signal),
    enabled: enabled && Boolean(user),
    retry: false,
  });
}
export function useDetail(path, id) {
  return useResource(`${path}/${id}`, {}, Boolean(id && id !== "moi"));
}
export function useCollection(path, initial = {}, transform = (params) => params) {
  const [params, setParams] = useState({ page: 1, page_size: 20, ...initial });
  const query = useResource(path, transform(params));
  return {
    query,
    params,
    filter: (next) => setParams((previous) => ({ ...previous, ...next, page: 1 })),
    setPage: (page) => setParams((previous) => ({ ...previous, page })),
    setPageSize: (page_size) =>
      setParams((previous) => ({ ...previous, page_size: Number(page_size), page: 1 })),
  };
}
export function useWrite() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: writeResource,
    retry: false,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["resources"] }),
    onError: (error) => {
      if (error.ticketId) return queryClient.invalidateQueries({ queryKey: ["resources"] });
    },
  });
}
export function useCatalog() {
  return useResource(API.catalog);
}
export function useChoices(path, params = {}, enabled = true) {
  const { user } = useAuth();
  return useQuery({
    queryKey: ["resources", user?.id, user?.ma_vai_tro, path, "choices", params],
    queryFn: ({ signal }) => readAll(path, params, signal),
    enabled: enabled && Boolean(user),
    retry: false,
  });
}
