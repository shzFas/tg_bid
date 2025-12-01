import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { getRequest, deleteRequest } from "../api/requests";
import { Request } from "../types";
import { Box, Typography, Button } from "@mui/material";
import { useNavigate } from "react-router-dom";

export default function RequestDetail() {
  const { id } = useParams();
  const [data, setData] = useState<Request | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    if (id) getRequest(id).then(setData);
  }, [id]);

  async function handleDelete() {
    if (id) {
      await deleteRequest(id);
      navigate("/requests");
    }
  }

  if (!data) return <p>Загрузка...</p>;

  return (
    <Box p={2}>
      <Typography variant="h5">Заявка #{data.id}</Typography>
      <Typography>Имя: {data.name}</Typography>
      <Typography>Телефон: {data.phone}</Typography>
      <Typography>Описание: {data.description}</Typography>
      <Typography>Статус: {data.status}</Typography>

      <Box mt={2}>
        <Button component={Link} to={`/requests/${id}/edit`} variant="contained">
          ✏ Редактировать
        </Button>{" "}
        <Button onClick={handleDelete} color="error" variant="contained">
          🗑 Удалить
        </Button>
      </Box>
    </Box>
  );
}
