import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { FileText, ArrowRight, Shield, Building2 } from "lucide-react";

const Signup = () => {
  const [formData, setFormData] = useState({
    // Required fields
    companyName: "",
    companyId: "",
    capabilitiesStatement: "",
    // Optional fields
    website: "",
    city: "",
    state: "",
    country: "",
    yearsOfExperience: "",
    teamSize: "",
    naicsCodes: "",
    capabilities: "",
    certifications: "",
    setAsideType: "",
    uei: "",
    cageCode: "",
    fullName: "",
    email: "",
    phone: "",
    address: "",
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.companyName.trim()) {
      setError("Company name is required");
      return;
    }
    if (!formData.companyId.trim()) {
      setError("Company ID is required");
      return;
    }
    if (!formData.capabilitiesStatement.trim()) {
      setError("Company description is required");
      return;
    }
    setLoading(true);
    setError("");
    try {
      const profileData: any = {
        companyName: formData.companyName.trim(),
        companyId: formData.companyId.trim(),
        capabilitiesStatement: formData.capabilitiesStatement.trim(),
      };

      // Optional fields - only include if provided
      if (formData.website.trim()) profileData.website = formData.website.trim();
      if (formData.yearsOfExperience.trim()) {
        profileData.yearsOfExperience = parseFloat(formData.yearsOfExperience) || 0;
      }
      if (formData.teamSize.trim()) {
        profileData.teamSize = parseInt(formData.teamSize) || 0;
      }
      if (formData.naicsCodes.trim()) {
        profileData.naicsCodes = formData.naicsCodes.split(",").map((c) => c.trim()).filter(Boolean);
      }
      if (formData.capabilities.trim()) {
        profileData.capabilities = formData.capabilities.split(",").map((c) => c.trim()).filter(Boolean);
      }
      if (formData.certifications.trim()) {
        profileData.certifications = formData.certifications.split(",").map((c) => c.trim()).filter(Boolean);
      }
      if (formData.setAsideType.trim()) profileData.setAsideType = formData.setAsideType.trim();
      if (formData.uei.trim()) profileData.uei = formData.uei.trim();
      if (formData.cageCode.trim()) profileData.cageCode = formData.cageCode.trim();

      // Location
      const location: any = {};
      if (formData.city.trim()) location.city = formData.city.trim();
      if (formData.state.trim()) location.state = formData.state.trim();
      if (formData.country.trim()) location.country = formData.country.trim();
      if (Object.keys(location).length > 0) profileData.location = location;

      // Contact
      const contact: any = {};
      if (formData.fullName.trim()) contact.fullName = formData.fullName.trim();
      if (formData.email.trim()) contact.email = formData.email.trim();
      if (formData.phone.trim()) contact.phone = formData.phone.trim();
      if (formData.address.trim()) contact.address = formData.address.trim();
      if (Object.keys(contact).length > 0) profileData.contact = contact;

      const res = await api.signup(profileData);
      setSuccess(true);

      // Auto-login after signup
      setTimeout(async () => {
        try {
          const loginRes = await api.login(res.companyId);
          login(loginRes.access_token, loginRes.companyId);
          navigate("/opportunities");
        } catch (err: any) {
          setError(`Account created but login failed: ${err.message}`);
          setSuccess(false);
        }
      }, 1000);
    } catch (err: any) {
      setError(err.message || "Signup failed. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-background px-4 py-8">
      <div className="w-full max-w-3xl fade-in">
        {/* Logo / Brand */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-primary mb-5">
            <FileText className="w-7 h-7 text-primary-foreground" />
          </div>
          <h1 className="text-3xl font-bold text-foreground mb-2">Create Account</h1>
          <p className="text-muted-foreground text-base">
            Sign up to start generating AI-powered government proposals
          </p>
        </div>

        {/* Signup Card */}
        <div className="glass-card p-8 max-h-[90vh] overflow-y-auto">
          {success ? (
            <div className="text-center space-y-4">
              <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-success/10 mb-4">
                <Shield className="w-8 h-8 text-success" />
              </div>
              <h2 className="text-xl font-semibold text-foreground">Account Created!</h2>
              <p className="text-muted-foreground">Logging you in...</p>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-5">
              {/* Required Fields Section */}
              <div className="space-y-4">
                <h3 className="text-sm font-semibold text-foreground border-b border-border pb-2">
                  Required Information
                </h3>

                <div>
                  <label htmlFor="companyName" className="block text-sm font-medium text-foreground mb-2">
                    Company Name <span className="text-destructive">*</span>
                  </label>
                  <Input
                    id="companyName"
                    name="companyName"
                    type="text"
                    placeholder="Enter your company name"
                    value={formData.companyName}
                    onChange={handleChange}
                    className="h-11"
                    required
                    autoFocus
                  />
                </div>

                <div>
                  <label htmlFor="companyId" className="block text-sm font-medium text-foreground mb-2">
                    Company ID <span className="text-destructive">*</span>
                  </label>
                  <Input
                    id="companyId"
                    name="companyId"
                    type="text"
                    placeholder="e.g., sg-security-001"
                    value={formData.companyId}
                    onChange={handleChange}
                    className="h-11"
                    required
                  />
                  <p className="text-xs text-muted-foreground mt-1">
                    This will be your login ID. Choose a unique identifier for your company.
                  </p>
                </div>

                <div>
                  <label htmlFor="capabilitiesStatement" className="block text-sm font-medium text-foreground mb-2">
                    Company Description <span className="text-destructive">*</span>
                  </label>
                  <Textarea
                    id="capabilitiesStatement"
                    name="capabilitiesStatement"
                    placeholder="Describe your company's capabilities, services, and expertise. This will be used to generate proposals that match your experience."
                    value={formData.capabilitiesStatement}
                    onChange={handleChange}
                    className="min-h-[120px]"
                    required
                  />
                  <p className="text-xs text-muted-foreground mt-1">
                    Include your services, past projects, certifications, and key capabilities.
                  </p>
                </div>
              </div>

              {/* Optional Fields Section */}
              <div className="space-y-4 pt-4 border-t border-border">
                <h3 className="text-sm font-semibold text-muted-foreground border-b border-border pb-2">
                  Optional Information
                </h3>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <label htmlFor="website" className="block text-sm font-medium text-foreground mb-2">
                      Website
                    </label>
                    <Input
                      id="website"
                      name="website"
                      type="url"
                      placeholder="https://example.com"
                      value={formData.website}
                      onChange={handleChange}
                      className="h-11"
                    />
                  </div>

                  <div>
                    <label htmlFor="setAsideType" className="block text-sm font-medium text-foreground mb-2">
                      Set-Aside Type
                    </label>
                    <Input
                      id="setAsideType"
                      name="setAsideType"
                      type="text"
                      placeholder="e.g., SDVOSB, WOSB, HUBZone"
                      value={formData.setAsideType}
                      onChange={handleChange}
                      className="h-11"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <label htmlFor="uei" className="block text-sm font-medium text-foreground mb-2">
                      UEI (Unique Entity Identifier)
                    </label>
                    <Input
                      id="uei"
                      name="uei"
                      type="text"
                      placeholder="12-character UEI"
                      value={formData.uei}
                      onChange={handleChange}
                      className="h-11"
                    />
                  </div>

                  <div>
                    <label htmlFor="cageCode" className="block text-sm font-medium text-foreground mb-2">
                      CAGE Code
                    </label>
                    <Input
                      id="cageCode"
                      name="cageCode"
                      type="text"
                      placeholder="5-character CAGE code"
                      value={formData.cageCode}
                      onChange={handleChange}
                      className="h-11"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <label htmlFor="yearsOfExperience" className="block text-sm font-medium text-foreground mb-2">
                      Years of Experience
                    </label>
                    <Input
                      id="yearsOfExperience"
                      name="yearsOfExperience"
                      type="number"
                      placeholder="e.g., 10"
                      value={formData.yearsOfExperience}
                      onChange={handleChange}
                      className="h-11"
                    />
                  </div>

                  <div>
                    <label htmlFor="teamSize" className="block text-sm font-medium text-foreground mb-2">
                      Team Size
                    </label>
                    <Input
                      id="teamSize"
                      name="teamSize"
                      type="number"
                      placeholder="e.g., 50"
                      value={formData.teamSize}
                      onChange={handleChange}
                      className="h-11"
                    />
                  </div>
                </div>

                <div>
                  <label htmlFor="naicsCodes" className="block text-sm font-medium text-foreground mb-2">
                    NAICS Codes
                  </label>
                  <Input
                    id="naicsCodes"
                    name="naicsCodes"
                    type="text"
                    placeholder="Comma-separated, e.g., 541511, 541611"
                    value={formData.naicsCodes}
                    onChange={handleChange}
                    className="h-11"
                  />
                  <p className="text-xs text-muted-foreground mt-1">
                    Enter NAICS codes separated by commas
                  </p>
                </div>

                <div>
                  <label htmlFor="capabilities" className="block text-sm font-medium text-foreground mb-2">
                    Capabilities
                  </label>
                  <Input
                    id="capabilities"
                    name="capabilities"
                    type="text"
                    placeholder="Comma-separated, e.g., IT Services, Cybersecurity, Project Management"
                    value={formData.capabilities}
                    onChange={handleChange}
                    className="h-11"
                  />
                  <p className="text-xs text-muted-foreground mt-1">
                    Enter capabilities separated by commas
                  </p>
                </div>

                <div>
                  <label htmlFor="certifications" className="block text-sm font-medium text-foreground mb-2">
                    Certifications
                  </label>
                  <Input
                    id="certifications"
                    name="certifications"
                    type="text"
                    placeholder="Comma-separated, e.g., Small Business, SDVOSB, ISO 9001"
                    value={formData.certifications}
                    onChange={handleChange}
                    className="h-11"
                  />
                  <p className="text-xs text-muted-foreground mt-1">
                    Enter certifications separated by commas
                  </p>
                </div>

                {/* Location */}
                <div className="space-y-2">
                  <label className="block text-sm font-medium text-foreground mb-2">Location</label>
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                    <Input
                      id="city"
                      name="city"
                      type="text"
                      placeholder="City"
                      value={formData.city}
                      onChange={handleChange}
                      className="h-11"
                    />
                    <Input
                      id="state"
                      name="state"
                      type="text"
                      placeholder="State"
                      value={formData.state}
                      onChange={handleChange}
                      className="h-11"
                    />
                    <Input
                      id="country"
                      name="country"
                      type="text"
                      placeholder="Country"
                      value={formData.country}
                      onChange={handleChange}
                      className="h-11"
                    />
                  </div>
                </div>

                {/* Contact */}
                <div className="space-y-2">
                  <label className="block text-sm font-medium text-foreground mb-2">Contact Information</label>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <Input
                      id="fullName"
                      name="fullName"
                      type="text"
                      placeholder="Full Name"
                      value={formData.fullName}
                      onChange={handleChange}
                      className="h-11"
                    />
                    <Input
                      id="email"
                      name="email"
                      type="email"
                      placeholder="Email"
                      value={formData.email}
                      onChange={handleChange}
                      className="h-11"
                    />
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <Input
                      id="phone"
                      name="phone"
                      type="tel"
                      placeholder="Phone"
                      value={formData.phone}
                      onChange={handleChange}
                      className="h-11"
                    />
                    <Input
                      id="address"
                      name="address"
                      type="text"
                      placeholder="Address"
                      value={formData.address}
                      onChange={handleChange}
                      className="h-11"
                    />
                  </div>
                </div>
              </div>

              {error && (
                <div className="text-sm text-destructive bg-destructive/10 rounded-lg px-3 py-2">
                  {error}
                </div>
              )}

              <Button
                type="submit"
                className="w-full h-11 text-sm font-medium"
                disabled={loading || !formData.companyName.trim() || !formData.companyId.trim() || !formData.capabilitiesStatement.trim()}
              >
                {loading ? (
                  <span className="flex items-center gap-2">
                    <span className="w-4 h-4 border-2 border-primary-foreground/30 border-t-primary-foreground rounded-full animate-spin" />
                    Creating account...
                  </span>
                ) : (
                  <span className="flex items-center gap-2">
                    <Building2 className="w-4 h-4" />
                    Create Account <ArrowRight className="w-4 h-4" />
                  </span>
                )}
              </Button>
            </form>
          )}

          {/* Login link */}
          <div className="mt-6 text-center">
            <p className="text-sm text-muted-foreground">
              Already have an account?{" "}
              <Link to="/login" className="text-primary hover:underline font-medium">
                Sign in
              </Link>
            </p>
          </div>
        </div>

        {/* Trust footer */}
        <div className="flex items-center justify-center gap-2 mt-6 text-xs text-muted-foreground">
          <Shield className="w-3.5 h-3.5" />
          <span>Secure, encrypted connection</span>
        </div>
      </div>
    </div>
  );
};

export default Signup;
