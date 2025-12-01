import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { getRequest, updateRequest } from "../api/requests";
import {
  Box, TextField, Button, MenuItem
} from "@mui/material";
import { useSnackbar } from "../components/SnackbarProvider";

const SPECIALIZATIONS = ["ACCOUNTING", "LAW", "EGOV"];

const SPEC_LABELS: Record<string, string> = {
  ACCOUNTING: "Бухгалтер",
  LAW: "Адвокат",
  EGOV: "Госуслуги (EGOV)",
};

export default function RequestEdit() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { showMessage } = useSnackbar();

  const [form, setForm] = useState<any>({});
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    async function load() {
      try {
        if (id) {
          const data = await getRequest(id);
          setForm(data);
        }
      } catch (err: any) {
        showMessage(err.message, "error");
      }
    }
    load();
  }, [id]);

  function handleChange(e: React.ChangeEvent<HTMLInputElement>) {
    setForm({ ...form, [e.target.name]: e.target.value });
  }

  async function handleSubmit() {
    if (!id) return;

    try {
      setLoading(true);

      await updateRequest(id, form);
      showMessage("Заявка успешно обновлена", "success");

      navigate("/requests");
    } catch (err: any) {
      showMessage(err.message, "error");
    } finally {
      setLoading(false);
    }
  }

  return (
    <Box p={2}>
      <TextField
        fullWidth
        label="Имя"
        name="name"
        value={form.name || ""}
        onChange={handleChange}
        sx={{ mb: 2 }}
      />

      <TextField
        fullWidth
        label="Телефон"
        name="phone"
        value={form.phone || ""}
        onChange={handleChange}
        sx={{ mb: 2 }}
      />

      <TextField
        fullWidth
        label="Город"
        name="city"
        value={form.city || ""}
        onChange={handleChange}
        sx={{ mb: 2 }}
      />

      <TextField
        fullWidth
        select
        label="Специализация"
        name="specialization"
        value={form.specialization || ""}
        onChange={handleChange}
        sx={{ mb: 2 }}
      >
        {SPECIALIZATIONS.map((spec) => (
          <MenuItem key={spec} value={spec}>
            {SPEC_LABELS[spec]}
          </MenuItem>
        ))}
      </TextField>

      <TextField
        fullWidth
        label="Описание"
        name="description"
        value={form.description || ""}
        multiline
        rows={3}
        onChange={handleChange}
      />

      <Button
        onClick={handleSubmit}
        variant="contained"
        sx={{ mt: 2 }}
        disabled={loading}
      >
        {loading ? "Сохранение..." : "Сохранить изменения"}
      </Button>
    </Box>
  );
}
