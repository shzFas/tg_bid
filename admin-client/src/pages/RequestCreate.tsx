import { useState } from "react";
import { createRequest } from "../api/requests";
import { useNavigate } from "react-router-dom";
import { Box, TextField, Button, MenuItem, Typography } from "@mui/material";
import { useSnackbar } from "../components/SnackbarProvider";

const SPECIALIZATIONS = ["ACCOUNTING", "LAW", "EGOV"];

const SPEC_LABELS: Record<string, string> = {
  ACCOUNTING: "Бухгалтер",
  LAW: "Адвокат",
  EGOV: "Госуслуги (EGOV)",
};

export default function RequestCreate() {
  const [form, setForm] = useState({
    name: "",
    phone: "",
    city: "",
    description: "",
    specialization: "ACCOUNTING",
  });

  const navigate = useNavigate();
  const { showMessage } = useSnackbar();
  const [loading, setLoading] = useState(false);

  function handleChange(e: React.ChangeEvent<HTMLInputElement>) {
    setForm({ ...form, [e.target.name]: e.target.value });
  }

  async function handleSubmit() {
    try {
      setLoading(true);

      await createRequest(form);

      showMessage("Заявка создана и опубликована", "success");
      navigate("/requests");
    } catch (err: any) {
      showMessage(err.message, "error");
    } finally {
      setLoading(false);
    }
  }

  return (
    <Box p={2} sx={{ maxWidth: 500 }}>
      <Typography variant="h5" sx={{ mb: 2 }}>
        Создать заявку
      </Typography>

      <TextField
        label="Имя"
        name="name"
        value={form.name}
        onChange={handleChange}
        fullWidth
        sx={{ mb: 2 }}
      />

      <TextField
        label="Телефон"
        name="phone"
        value={form.phone}
        onChange={handleChange}
        fullWidth
        sx={{ mb: 2 }}
      />

      <TextField
        label="Город"
        name="city"
        value={form.city}
        onChange={handleChange}
        fullWidth
        sx={{ mb: 2 }}
      />

      <TextField
        label="Специализация"
        name="specialization"
        value={form.specialization}
        onChange={handleChange}
        select
        fullWidth
        sx={{ mb: 2 }}
      >
        {SPECIALIZATIONS.map((spec) => (
          <MenuItem key={spec} value={spec}>
            {SPEC_LABELS[spec]}
          </MenuItem>
        ))}
      </TextField>

      <TextField
        label="Описание"
        name="description"
        value={form.description}
        onChange={handleChange}
        fullWidth
        multiline
        rows={3}
      />

      <Button
        onClick={handleSubmit}
        variant="contained"
        sx={{ mt: 3 }}
        fullWidth
        disabled={loading}
      >
        {loading ? "Создание..." : "Создать"}
      </Button>
    </Box>
  );
}
