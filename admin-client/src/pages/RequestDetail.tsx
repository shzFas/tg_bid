import { useEffect, useState } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import { getRequest, deleteRequest } from "../api/requests";
import { Request } from "../types";
import { Box, Typography, Button } from "@mui/material";
import { useSnackbar } from "../components/SnackbarProvider";

export default function RequestDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { showMessage } = useSnackbar();

  const [data, setData] = useState<Request | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    async function load() {
      try {
        if (id) {
          const req = await getRequest(id);
          setData(req);
        }
      } catch (err: any) {
        showMessage(err.message, "error");
        navigate("/requests"); // безопасно возвращаем пользователя
      }
    }
    load();
  }, [id]);

  async function handleDelete() {
    if (!id) return;

    try {
      setLoading(true);

      await deleteRequest(id);
      showMessage("Заявка удалена", "success");

      navigate("/requests");
    } catch (err: any) {
      showMessage(err.message, "error");
    } finally {
      setLoading(false);
    }
  }

  if (!data) return <p>Загрузка...</p>;

  return (
    <Box p={2}>
      <Typography variant="h5">Заявка #{data.id}</Typography>

      <Typography><b>Имя:</b> {data.name}</Typography>
      <Typography><b>Телефон:</b> {data.phone}</Typography>
      <Typography><b>Описание:</b> {data.description}</Typography>
      <Typography><b>Статус:</b> {data.status}</Typography>
      <Typography><b>Категория:</b> {data.specialization}</Typography>

      <Box mt={2}>
        <Button
          component={Link}
          to={`/requests/${id}/edit`}
          variant="contained"
        >
          ✏ Редактировать
        </Button>{" "}

        <Button
          onClick={handleDelete}
          color="error"
          variant="contained"
          disabled={loading}
        >
          {loading ? "Удаление..." : "🗑 Удалить"}
        </Button>
      </Box>
    </Box>
  );
}
