import { Specialist } from "../types";
import { api } from "./axios";

export async function getAllSpecialists(): Promise<Specialist[]> {
  return api.get("/specialists");
}

export async function getSpecialist(id: number): Promise<Specialist> {
  return api.get(`/specialists/${id}`);
}

export async function createSpecialist(
  data: Partial<Specialist>
): Promise<Specialist> {
  return api.post("/specialists", data);
}

export async function updateSpecialist(
  id: number,
  data: Partial<Specialist>
): Promise<Specialist> {
  return api.put(`/specialists/${id}`, data);
}

export async function deleteSpecialist(
  id: number
): Promise<{ id: number }> {
  return api.delete(`/specialists/${id}`);
}

export async function approveSpecialist(
  id: number
): Promise<{ approved: true }> {
  return api.post(`/specialists/${id}/approve`, {
    is_approved: true,
  });
}
