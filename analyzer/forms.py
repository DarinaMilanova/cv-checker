from django import forms


class AnalyzeUploadForm(forms.Form):
    job_title = forms.CharField(
        label="Job Title",
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "e.g. Senior Frontend Engineer",
        }),
    )
    company = forms.CharField(
        label="Company",
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "e.g. Acme Corp",
        }),
    )

    cv = forms.FileField(label="CV (PDF/DOCX/RTF/TXT)", required=False)
    jd = forms.FileField(label="Job Description (PDF/DOCX/RTF/TXT)", required=False)

    cv_text = forms.CharField(
        label="Or paste your CV text here",
        widget=forms.Textarea(attrs={"rows": 6}),
        required=False,
    )
    jd_text = forms.CharField(
        label="Or paste Job Description text here",
        widget=forms.Textarea(attrs={"rows": 6}),
        required=False,
    )

    def clean(self):
        cleaned = super().clean()
        cv, jd = cleaned.get("cv"), cleaned.get("jd")
        cv_text, jd_text = cleaned.get("cv_text"), cleaned.get("jd_text")

        if cv_text:
            cleaned["cv_text"] = cv_text.strip()
        if jd_text:
            cleaned["jd_text"] = jd_text.strip()

        if not (cv or cleaned.get("cv_text")):
            raise forms.ValidationError("You must provide either a CV file or CV text.")
        if not (jd or cleaned.get("jd_text")):
            raise forms.ValidationError("You must provide either a JD file or JD text.")

        return cleaned