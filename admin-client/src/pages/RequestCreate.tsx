import { useState } from "react";
import { createRequest } from "../api/requests";
import { useNavigate } from "react-router-dom";
import { Box, TextField, Button } from "@mui/material";

export default function RequestCreate() {
  const [form, setForm] = useState({ name: "", phone: "", description: "" });
  const navigate = useNavigate();

  function handleChange(e: React.ChangeEvent<HTMLInputElement>) {
    setForm({ ...form, [e.target.name]: e.target.value });
  }

  async function handleSubmit() {
    await createRequest(form);
    navigate("/requests");
  }

  return (
    <Box p={2}>
      <TextField label="Имя" name="name" onChange={handleChange} fullWidth sx={{ mb: 2 }} />
      <TextField label="Телефон" name="phone" onChange={handleChange} fullWidth sx={{ mb: 2 }} />
      <TextField label="Описание" name="description" onChange={handleChange} fullWidth multiline rows={3} />
    
      <Button onClick={handleSubmit} variant="contained" sx={{ mt: 2 }}>
        Создать
      </Button>
    </Box>
  );
}
