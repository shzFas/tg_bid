import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { getRequest, updateRequest } from "../api/requests";
import { Box, TextField, Button } from "@mui/material";

export default function RequestEdit() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [form, setForm] = useState<any>({});

  useEffect(() => {
    if (id) getRequest(id).then(setForm);
  }, [id]);

  function handleChange(e: React.ChangeEvent<HTMLInputElement>) {
    setForm({ ...form, [e.target.name]: e.target.value });
  }

  async function handleSubmit() {
    if (id) {
      await updateRequest(id, form);
      navigate(`/requests/${id}`);
    }
  }

  return (
    <Box p={2}>
      <TextField label="Имя" name="name" value={form.name || ""} onChange={handleChange} fullWidth sx={{ mb: 2 }} />
      <TextField label="Телефон" name="phone" value={form.phone || ""} onChange={handleChange} fullWidth sx={{ mb: 2 }} />
      <TextField label="Описание" name="description" value={form.description || ""} onChange={handleChange} fullWidth multiline rows={3} />

      <Button onClick={handleSubmit} variant="contained" sx={{ mt: 2 }}>
        Сохранить изменения
      </Button>
    </Box>
  );
}
