import createClient from "openapi-fetch";
import type { paths } from "./generated/schema";

export const http = createClient<paths>({ baseUrl: "/" });
