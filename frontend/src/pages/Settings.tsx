import React, { useState } from "react";
import { useSelector } from "react-redux";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { 
  User as UserIcon, 
  Shield, 
  UserPlus, 
  Trash2, 
  ToggleLeft, 
  ToggleRight, 
  CheckCircle, 
  AlertCircle,
  X
} from "lucide-react";
import api from "../services/api.ts";
import { RootState } from "../store/index.ts";
import DashboardLayout from "../components/DashboardLayout.tsx";

interface UserItem {
  id: string;
  email: string;
  full_name: string | null;
  role: string;
  is_active: boolean;
  is_verified: boolean;
  created_at: string;
}

const Settings: React.FC = () => {
  const queryClient = useQueryClient();
  const { user: currentUser } = useSelector((state: RootState) => state.auth);
  
  const [activeTab, setActiveTab] = useState<"profile" | "admin">(
    currentUser?.role === "admin" ? "admin" : "profile"
  );
  
  // Modals & Forms state
  const [showAddModal, setShowAddModal] = useState(false);
  const [newUserEmail, setNewUserEmail] = useState("");
  const [newUserPassword, setNewUserPassword] = useState("");
  const [newUserFullName, setNewUserFullName] = useState("");
  const [newUserRole, setNewUserRole] = useState("user");
  
  // Alert states
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // 1. Query all users (Admin only)
  const { data: users, isLoading: usersLoading } = useQuery<UserItem[]>({
    queryKey: ["users"],
    queryFn: async () => {
      const res = await api.get("/users/");
      return res.data;
    },
    enabled: currentUser?.role === "admin"
  });

  // 2. Create User Mutation
  const createUserMutation = useMutation({
    mutationFn: async () => {
      const res = await api.post("/users/", {
        email: newUserEmail,
        password: newUserPassword,
        full_name: newUserFullName || null,
        role: newUserRole,
        is_active: true,
        is_verified: true
      });
      return res.data;
    },
    onSuccess: () => {
      setSuccessMsg("User created successfully!");
      setShowAddModal(false);
      // Reset form
      setNewUserEmail("");
      setNewUserPassword("");
      setNewUserFullName("");
      setNewUserRole("user");
      
      queryClient.invalidateQueries({ queryKey: ["users"] });
      setTimeout(() => setSuccessMsg(null), 3000);
    },
    onError: (err: any) => {
      setErrorMsg(err.response?.data?.detail || "Failed to create user.");
      setTimeout(() => setErrorMsg(null), 4000);
    }
  });

  // 3. Toggle Active Mutation
  const toggleActiveMutation = useMutation({
    mutationFn: async ({ userId, is_active }: { userId: string; is_active: boolean }) => {
      const res = await api.put(`/users/${userId}`, {
        is_active
      });
      return res.data;
    },
    onSuccess: () => {
      setSuccessMsg("User status updated!");
      queryClient.invalidateQueries({ queryKey: ["users"] });
      setTimeout(() => setSuccessMsg(null), 3000);
    },
    onError: (err: any) => {
      setErrorMsg(err.response?.data?.detail || "Failed to update user status.");
      setTimeout(() => setErrorMsg(null), 4000);
    }
  });

  // 4. Delete User Mutation
  const deleteUserMutation = useMutation({
    mutationFn: async (userId: string) => {
      const res = await api.delete(`/users/${userId}`);
      return res.data;
    },
    onSuccess: () => {
      setSuccessMsg("User deleted successfully.");
      queryClient.invalidateQueries({ queryKey: ["users"] });
      setTimeout(() => setSuccessMsg(null), 3000);
    },
    onError: (err: any) => {
      setErrorMsg(err.response?.data?.detail || "Failed to delete user.");
      setTimeout(() => setErrorMsg(null), 4000);
    }
  });

  const handleCreateUser = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newUserEmail || !newUserPassword) {
      setErrorMsg("Email and password are required.");
      setTimeout(() => setErrorMsg(null), 3000);
      return;
    }
    createUserMutation.mutate();
  };

  const handleToggleActive = (userId: string, currentStatus: boolean) => {
    if (userId === currentUser?.id) {
      setErrorMsg("You cannot deactivate your own account.");
      setTimeout(() => setErrorMsg(null), 3000);
      return;
    }
    toggleActiveMutation.mutate({ userId, is_active: !currentStatus });
  };

  const handleDeleteUser = (userId: string) => {
    if (userId === currentUser?.id) {
      setErrorMsg("You cannot delete your own account.");
      setTimeout(() => setErrorMsg(null), 3000);
      return;
    }
    if (window.confirm("Are you sure you want to delete this user?")) {
      deleteUserMutation.mutate(userId);
    }
  };

  return (
    <DashboardLayout>
      <div className="max-w-6xl mx-auto flex flex-col md:flex-row gap-6">
        
        {/* Left pane: Navigation tabs */}
        <div className="w-full md:w-64 shrink-0 flex flex-col gap-2">
          <div className="bg-surface border border-border p-4 rounded-xl space-y-1">
            <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3 px-2">Settings Menu</h3>
            
            <button
              onClick={() => setActiveTab("profile")}
              className={`w-full text-left px-3.5 py-2.5 rounded-lg text-sm transition-all flex items-center gap-2 border ${
                activeTab === "profile"
                  ? "bg-primary/10 border-primary/30 text-primary font-bold"
                  : "bg-transparent border-transparent text-slate-400 hover:bg-slate-800/40 hover:text-white"
              }`}
            >
              <UserIcon size={16} />
              My Profile
            </button>

            {currentUser?.role === "admin" && (
              <button
                onClick={() => setActiveTab("admin")}
                className={`w-full text-left px-3.5 py-2.5 rounded-lg text-sm transition-all flex items-center gap-2 border ${
                  activeTab === "admin"
                    ? "bg-primary/10 border-primary/30 text-primary font-bold"
                    : "bg-transparent border-transparent text-slate-400 hover:bg-slate-800/40 hover:text-white"
                }`}
              >
                <Shield size={16} />
                User Management
              </button>
            )}
          </div>
        </div>

        {/* Right pane: Content Panel */}
        <div className="flex-1 min-w-0">
          {successMsg && (
            <div className="mb-4 p-3.5 bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 rounded-xl text-xs font-semibold flex items-center gap-2">
              <CheckCircle size={16} />
              <span>{successMsg}</span>
            </div>
          )}
          {errorMsg && (
            <div className="mb-4 p-3.5 bg-rose-500/10 border border-rose-500/30 text-rose-400 rounded-xl text-xs font-semibold flex items-center gap-2">
              <AlertCircle size={16} />
              <span>{errorMsg}</span>
            </div>
          )}

          {/* TAB: PROFILE */}
          {activeTab === "profile" && (
            <div className="bg-surface border border-border p-6 rounded-xl space-y-6">
              <div>
                <h2 className="text-lg font-bold text-slate-100">Account Profile</h2>
                <p className="text-xs text-slate-400 mt-1">Details of your logged-in ShareBot profile.</p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6 pt-2">
                <div className="bg-slate-900/50 border border-border/40 p-4 rounded-xl space-y-1">
                  <span className="block text-[10px] text-slate-500 font-bold uppercase tracking-wider">Email Address</span>
                  <span className="text-sm font-semibold text-slate-200">{currentUser?.email}</span>
                </div>

                <div className="bg-slate-900/50 border border-border/40 p-4 rounded-xl space-y-1">
                  <span className="block text-[10px] text-slate-500 font-bold uppercase tracking-wider">Full Name</span>
                  <span className="text-sm font-semibold text-slate-200">{currentUser?.full_name || "N/A"}</span>
                </div>

                <div className="bg-slate-900/50 border border-border/40 p-4 rounded-xl space-y-1">
                  <span className="block text-[10px] text-slate-500 font-bold uppercase tracking-wider">Account Role</span>
                  <span className="text-sm font-semibold text-primary capitalize flex items-center gap-1.5 mt-0.5">
                    <Shield size={14} />
                    {currentUser?.role || "user"}
                  </span>
                </div>
              </div>
            </div>
          )}

          {/* TAB: ADMIN (USER MANAGEMENT) */}
          {activeTab === "admin" && currentUser?.role === "admin" && (
            <div className="bg-surface border border-border p-6 rounded-xl space-y-6">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-lg font-bold text-slate-100">User Management</h2>
                  <p className="text-xs text-slate-400 mt-1">Superuser panel to review registered accounts, activate/deactivate users, and add new credentials.</p>
                </div>
                <button
                  onClick={() => setShowAddModal(true)}
                  className="bg-primary hover:bg-primary-hover text-white text-xs font-bold px-3.5 py-2.5 rounded-lg flex items-center gap-1.5 transition-all"
                >
                  <UserPlus size={14} />
                  Add New User
                </button>
              </div>

              {usersLoading ? (
                <div className="py-20 text-center text-xs text-slate-500">Loading user database...</div>
              ) : (
                <div className="overflow-x-auto border border-border/40 rounded-xl bg-slate-900/20">
                  <table className="w-full text-left text-xs border-collapse">
                    <thead>
                      <tr className="border-b border-border/50 text-slate-400 uppercase text-[10px] font-bold bg-slate-900/40">
                        <th className="py-3 px-4">Name</th>
                        <th className="py-3 px-4">Email</th>
                        <th className="py-3 px-4">Role</th>
                        <th className="py-3 px-4">Status</th>
                        <th className="py-3 px-4">Joined At</th>
                        <th className="py-3 px-4 text-center">Actions</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border/30">
                      {users?.map((usr) => (
                        <tr key={usr.id} className="hover:bg-slate-900/30 text-slate-200 transition-colors">
                          <td className="py-3.5 px-4 font-semibold">{usr.full_name || "N/A"}</td>
                          <td className="py-3.5 px-4">{usr.email}</td>
                          <td className="py-3.5 px-4">
                            <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase border ${
                              usr.role === "admin" 
                                ? "bg-rose-500/10 border-rose-500/20 text-rose-400"
                                : "bg-slate-800 border-border text-slate-400"
                            }`}>
                              {usr.role}
                            </span>
                          </td>
                          <td className="py-3.5 px-4">
                            <button
                              onClick={() => handleToggleActive(usr.id, usr.is_active)}
                              className="focus:outline-none flex items-center gap-1"
                              title="Click to toggle status"
                            >
                              {usr.is_active ? (
                                <span className="text-emerald-400 font-bold flex items-center gap-1">
                                  <ToggleRight size={18} className="text-emerald-500" />
                                  Active
                                </span>
                              ) : (
                                <span className="text-slate-500 flex items-center gap-1">
                                  <ToggleLeft size={18} className="text-slate-500" />
                                  Inactive
                                </span>
                              )}
                            </button>
                          </td>
                          <td className="py-3.5 px-4 text-slate-400">
                            {new Date(usr.created_at).toLocaleDateString()}
                          </td>
                          <td className="py-3.5 px-4 text-center">
                            <button
                              onClick={() => handleDeleteUser(usr.id)}
                              disabled={usr.id === currentUser?.id}
                              className="text-slate-500 hover:text-rose-400 disabled:opacity-30 disabled:hover:text-slate-500 p-1.5 transition-colors"
                              title={usr.id === currentUser?.id ? "Cannot delete self" : "Delete user"}
                            >
                              <Trash2 size={15} />
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* ADD USER MODAL POPUP */}
      {showAddModal && (
        <div className="fixed inset-0 bg-background/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-surface border border-border p-6 rounded-2xl w-full max-w-md relative animate-in fade-in zoom-in duration-200">
            <button
              onClick={() => setShowAddModal(false)}
              className="absolute top-4 right-4 text-slate-400 hover:text-white transition-colors"
            >
              <X size={18} />
            </button>

            <h3 className="text-md font-extrabold text-slate-100 mb-1 flex items-center gap-2">
              <UserPlus size={18} className="text-primary" />
              Add New User Account
            </h3>
            <p className="text-[11px] text-slate-400 mb-5">Create new credentials to grant platform access.</p>

            <form onSubmit={handleCreateUser} className="space-y-4">
              <div>
                <label className="block text-[10px] text-slate-500 font-bold uppercase tracking-wider mb-1.5">Email Address</label>
                <input
                  type="email"
                  required
                  value={newUserEmail}
                  onChange={(e) => setNewUserEmail(e.target.value)}
                  placeholder="name@example.com"
                  className="w-full p-2.5 bg-slate-900 border border-border rounded-xl text-slate-200 focus:outline-none focus:border-primary transition-all text-xs"
                />
              </div>

              <div>
                <label className="block text-[10px] text-slate-500 font-bold uppercase tracking-wider mb-1.5">Password</label>
                <input
                  type="password"
                  required
                  value={newUserPassword}
                  onChange={(e) => setNewUserPassword(e.target.value)}
                  placeholder="••••••••"
                  className="w-full p-2.5 bg-slate-900 border border-border rounded-xl text-slate-200 focus:outline-none focus:border-primary transition-all text-xs"
                />
              </div>

              <div>
                <label className="block text-[10px] text-slate-500 font-bold uppercase tracking-wider mb-1.5">Full Name</label>
                <input
                  type="text"
                  value={newUserFullName}
                  onChange={(e) => setNewUserFullName(e.target.value)}
                  placeholder="e.g. John Doe"
                  className="w-full p-2.5 bg-slate-900 border border-border rounded-xl text-slate-200 focus:outline-none focus:border-primary transition-all text-xs"
                />
              </div>

              <div>
                <label className="block text-[10px] text-slate-500 font-bold uppercase tracking-wider mb-1.5">Access Role</label>
                <select
                  value={newUserRole}
                  onChange={(e) => setNewUserRole(e.target.value)}
                  className="w-full p-2.5 bg-slate-900 border border-border rounded-xl text-slate-200 focus:outline-none focus:border-primary transition-all text-xs cursor-pointer"
                >
                  <option value="user">User (Standard Trading Access)</option>
                  <option value="admin">Admin (Superuser Database Panel)</option>
                </select>
              </div>

              <div className="flex gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  className="flex-1 bg-slate-800 hover:bg-slate-700 border border-border text-slate-300 font-semibold py-2 rounded-xl text-xs transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={createUserMutation.isPending}
                  className="flex-1 bg-primary hover:bg-primary-hover text-white font-bold py-2 rounded-xl text-xs transition-colors flex items-center justify-center gap-1.5"
                >
                  {createUserMutation.isPending ? "Creating..." : "Create Account"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </DashboardLayout>
  );
};

export default Settings;
