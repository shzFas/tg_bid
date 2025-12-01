import axios from "axios";

const API_URL = "http://localhost:5000/api/specialists";

export async function getAllSpecialists() {
  const res = await axios.get(`${API_URL}`);
  return res.data;
}

export async function getSpecialist(id: number) {
  const res = await axios.get(`${API_URL}/${id}`);
  return res.data;
}

export async function createSpecialist(data: any) {
  const res = await axios.post(`${API_URL}`, data);
  return res.data;
}

export async function updateSpecialist(id: number, data: any) {
  const res = await axios.put(`${API_URL}/${id}`, data);
  return res.data;
}

export async function deleteSpecialist(id: number) {
  const res = await axios.delete(`${API_URL}/${id}`);
  return res.data;
}

export async function approveSpecialist(id: number) {
  const res = await axios.put(`${API_URL}/${id}/approve`, { is_approved: true });
  return res.data;
}
