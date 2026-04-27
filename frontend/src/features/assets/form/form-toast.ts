export const TOAST = {
  CREATE_SUCCESS: '登记成功',
  UPDATE_SUCCESS: '更新成功',
  DELETE_SUCCESS: '删除成功',
  STATUS_CHANGE_SUCCESS: '状态已切换',
  UPLOAD_SUCCESS: '附件上传成功',
  GENERIC_FAILURE: '操作失败，请重试',
  FILE_TOO_LARGE: '文件超过 10MB 限制',
  UNSUPPORTED_TYPE: '不支持的文件类型',
} as const;

export const PENDING_TEXT = {
  CREATE: '登记中…',
  UPDATE: '保存中…',
  DELETE: '删除中…',
} as const;
