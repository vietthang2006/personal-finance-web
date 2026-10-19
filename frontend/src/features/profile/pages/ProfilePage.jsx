import ProfileForm from "../components/ProfileForm";
import ChangePasswordForm from "../components/ChangePasswordForm";

export default function ProfilePage() {
  return (
    <div className="mx-auto max-w-lg space-y-6">
      <div className="rounded-xl bg-white p-6 shadow">
        <ProfileForm />
      </div>
      <div className="rounded-xl bg-white p-6 shadow">
        <ChangePasswordForm />
      </div>
    </div>
  );
}