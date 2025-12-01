import axios from "axios";
import { Request } from "../types";

const API_URL = "http://localhost:5000/api/requests";

export async function getRequests(): Promise<Request[]> {
  const res = await axios.get(API_URL);
  return res.data;
}

export async function getRequest(id: string): Promise<Request> {
  const res = await axios.get(`${API_URL}/${id}`);
  return res.data;
}

export async function createRequest(data: Partial<Request>) {
  const res = await axios.post(API_URL, data);
  return res.data;
}

export async function updateRequest(id: string, data: Partial<Request>) {
  const res = await axios.put(`${API_URL}/${id}`, data);
  return res.data;
}

export async function deleteRequest(id: string) {
  const res = await axios.delete(`${API_URL}/${id}`);
  return res.data;
}
