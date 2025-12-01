import { api } from "./axios";
import { Request } from "../types";

export async function getRequests(): Promise<Request[]> {
  return api.get("/requests");
}

export async function getRequest(id: string): Promise<Request> {
  return api.get(`/requests/${id}`);
}

export async function createRequest(data: Partial<Request>) {
  return api.post("/requests/create-and-publish", data);
}

export async function updateRequest(id: string, data: Partial<Request>) {
  return api.put(`/requests/${id}/publish-update`, data);
}

export async function deleteRequest(id: string) {
  return api.delete(`/requests/${id}`);
}
