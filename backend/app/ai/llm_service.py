import json
import os


class LLMService:
    def __init__(self):
        self.provider = os.getenv("AI_PROVIDER", "qwen").lower()
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.qwen_model = os.getenv("QWEN_MODEL", "Qwen/Qwen2.5-1.5B-Instruct")
        self.qwen_tokenizer = None
        self.qwen_model_instance = None
        self.client = None
        if self.provider == "openai" and self.api_key:
            from openai import OpenAI

            self.client = OpenAI(api_key=self.api_key)

    def _load_qwen(self):
        if self.qwen_model_instance is not None:
            return

        try:
            import torch
            from transformers import AutoModelForCausalLM, AutoTokenizer
        except ImportError as exc:
            raise RuntimeError(
                "Qwen is not installed. Run: pip install -r requirements.txt"
            ) from exc

        self.qwen_tokenizer = AutoTokenizer.from_pretrained(self.qwen_model)
        dtype = torch.float16 if torch.cuda.is_available() else torch.float32
        self.qwen_model_instance = AutoModelForCausalLM.from_pretrained(
            self.qwen_model,
            torch_dtype=dtype,
        )
        if torch.cuda.is_available():
            self.qwen_model_instance = self.qwen_model_instance.to("cuda")
        self.qwen_model_instance.eval()

    def _qwen_json(self, system_prompt: str, payload: dict) -> dict:
        self._load_qwen()
        import torch

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": json.dumps(payload)},
        ]
        prompt = self.qwen_tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
        )
        inputs = self.qwen_tokenizer(prompt, return_tensors="pt")
        device = next(self.qwen_model_instance.parameters()).device
        inputs = {name: value.to(device) for name, value in inputs.items()}
        with torch.inference_mode():
            output = self.qwen_model_instance.generate(
                **inputs,
                max_new_tokens=700,
                do_sample=False,
                pad_token_id=self.qwen_tokenizer.eos_token_id,
            )
        generated = output[0][inputs["input_ids"].shape[1]:]
        content = self.qwen_tokenizer.decode(generated, skip_special_tokens=True).strip()
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            start = content.find("{")
            end = content.rfind("}")
            if start < 0 or end <= start:
                raise ValueError("Qwen returned invalid JSON")
            return json.loads(content[start:end + 1])

    def analyze_resume(self, resume_text: str, deterministic_analysis: dict) -> dict:
        prompt = {
            "resume_text": resume_text[:12000],
            "required_output": {
                "skills": [{
                    "name": "canonical skill name",
                    "category": "Programming Language, Framework, Database, Tool, Cloud, AI/ML, or other",
                    "evidence": "exact or near-exact evidence from the resume",
                    "confidence": 0.0,
                }],
                "education": [],
                "experience": [],
                "internships": [],
                "projects": [],
                "certifications": [],
                "achievements": [],
                "suggested_roles": [],
                "domains": [],
            },
        }
        if self.provider == "qwen":
            result = self._qwen_json(
                "You extract only facts explicitly present in a resume. Do not invent information. "
                "Return only valid JSON matching required_output; use empty arrays when information is absent.",
                prompt,
            )
            result["status"] = "complete"
            result["provider"] = "qwen"
            return result

        if self.client is None:
            return {
                "status": "not_configured",
                "message": "Set OPENAI_API_KEY to enable AI resume evaluation.",
            }

        response = self.client.chat.completions.create(
            model=self.model,
            temperature=0.2,
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": "You are a practical technical recruiter. Return only valid JSON matching the requested output.",
                },
                {"role": "user", "content": json.dumps(prompt)},
            ],
        )
        content = response.choices[0].message.content or "{}"
        result = json.loads(content)
        result["status"] = "complete"
        return result

    def recommend_for_job(self, job_description: str, resume_analysis: dict) -> dict:
        prompt = {
            "job_description": job_description[:12000],
            "resume_analysis": resume_analysis,
            "required_output": {
                "overall_fit": "score between 0 and 100",
                "key_matches": ["skills and experiences that align with the job"],
                "gaps": ["missing skills or weak areas"],
                "recommendation": "summary of why the candidate is a fit",
                "next_steps": ["specific actions to improve fit"],
            },
        }
        if self.provider == "qwen":
            result = self._qwen_json(
                "You are a hiring advisor. Return only valid JSON with evidence from the resume.",
                prompt,
            )
            result["status"] = "complete"
            result["provider"] = "qwen"
            return result

        if self.client is None:
            return {
                "status": "not_configured",
                "message": "Set OPENAI_API_KEY to enable AI job-to-resume recommendations.",
            }


        response = self.client.chat.completions.create(
            model=self.model,
            temperature=0.2,
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": "You are a hiring advisor. Recommend fit between a candidate and a job with clear evidence from the resume.",
                },
                {"role": "user", "content": json.dumps(prompt)},
            ],
        )
        content = response.choices[0].message.content or "{}"
        result = json.loads(content)
        result["status"] = "complete"
        return result

    def generate_resume(self, name: str, user_choice: str) -> dict:
        prompt = {
            "candidate_name": name,
            "candidate_input": user_choice[:6000],
            "rules": [
                "Create a professional resume using only facts supplied by the candidate.",
                "Never invent employers, dates, degrees, certifications, metrics, or technologies.",
                "Use empty arrays or null for missing information.",
                "Make the formatted_resume ATS-friendly and professional.",
            ],
            "required_output": {
                "name": name,
                "headline": "target professional headline",
                "summary": "professional summary based only on supplied facts",
                "skills": [],
                "experience": [],
                "projects": [],
                "education": [],
                "certifications": [],
                "achievements": [],
                "domains": [],
                "formatted_resume": "plain-text resume",
            },
        }
        if self.provider == "qwen":
            result = self._qwen_json(
                "You are a professional resume writer. Return only valid JSON. "
                "Do not fabricate details that are not in the candidate input.",
                prompt,
            )
            result["status"] = "complete"
            result["provider"] = "qwen"
            return result

        if self.client is None:
            return {
                "status": "not_configured",
                "message": "Set OPENAI_API_KEY to enable CV generation.",
            }

        response = self.client.chat.completions.create(
            model=self.model,
            temperature=0.2,
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": "You are a professional resume writer. Return only valid JSON and never invent details.",
                },
                {"role": "user", "content": json.dumps(prompt)},
            ],
        )
        result = json.loads(response.choices[0].message.content or "{}")
        result["status"] = "complete"
        result["provider"] = "openai"
        return result
