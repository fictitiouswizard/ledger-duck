import { z } from "zod";
import { fail, redirect } from "@sveltejs/kit";

const registerSchema = z.object({
        username: z.string().trim()
            .min(8, {message: "Username must be 8 characters long"})
            .max(20, {message: "Username must be 20 characters long"}),
        password: z.string().trim().regex(
            /^(?=.*[A-Z])(?=.*[0-9])(?=.*[a-z]).{8,}$/,
            {
                message: "Password must be at least 8 characters long and contain an uppercase letter, lowercase letter, and number"
            }
        ),
        email: z.string().trim().email({message: "Invalid email address"})

    }
)

/** @type {import('./$types').Actions } */
export const actions = {
    default: async ({ request, fetch}) => {
        const formData = Object.fromEntries(await request.formData());
        const safeParse = registerSchema.safeParse(formData);
        if (!safeParse.success) {
            console.log(safeParse.error.issues)
            return fail(400, {issues: safeParse.error.issues});
        }
        const {username, password, email} = safeParse.data;
        const payload = JSON.stringify({
            username,
            password,
            email
        });
        const response = await fetch(
            "http://127.0.0.1:8000/register",
            {
                method: "POST",
                headers: {
                    'Accept': 'application/json',
                    'Content-Type': 'application/json'
                },
                body: payload
            }
        );
        const responseJson = await response.json();
        console.log(responseJson);
        redirect("303", "/login")
    }

}