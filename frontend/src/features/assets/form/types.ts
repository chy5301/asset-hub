/**
 * AssetType.custom_fields 的元素结构（与后端 CustomFieldDef 1:1 对齐）。
 *
 * 字段名 `key` 是 wire format 决议（M2c-3 Task 2 review）：M1/M2 老 fixtures
 * + 后端 validation.py 读 `f["key"]`，spec D2 informal 用了 "name" 不算数。
 */
export type FieldDef = {
  /** 字段名（schema 标识符）；不含单位后缀 */
  key: string;
  /** 显示名（用户看到），缺省 = key */
  label?: string;
  type: 'string' | 'text' | 'int' | 'float' | 'bool' | 'date' | 'enum' | 'multi-enum' | 'url';
  required?: boolean;
  default?: string | number | boolean | null;
  placeholder?: string;
  help?: string;
  /** 仅 int/float 用，input 内右侧 muted 显示，不参与校验 */
  unit?: string;
  /** 仅 int/float */
  min?: number;
  /** 仅 int/float */
  max?: number;
  /** 仅 enum / multi-enum */
  options?: string[];
  /** 仅 enum / multi-enum override 默认阈值（≤4 RadioGroup / ≥5 Select） */
  displayAs?: 'radio' | 'select';
};
